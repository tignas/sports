import re
import csv
import copy
import datetime
import json
import urllib, urllib2
from BeautifulSoup import BeautifulSoup
from sqlalchemy.orm import eagerload
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from connect_db import *
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.fantasy import *
from pprint import pprint

session = create_session()

def process_espn(body, fantasy_proj):
    players = body.findAll('tr', attrs={'class':re.compile('pncPlayerRow')})
    if not players:
        return True
    for player in players:        
        row = player.findAll('td')
        (rk, player_info, pass_c_a, pass_yds, pass_tds, pass_ints, 
        rush_att, rush_yds, rush_tds, rec_recs, rec_yds, rec_tds, pts) = row
        external_id = player_info['id'].partition('_')[2]
        #Player
        pass_c, pass_a = pass_c_a.text.split('/')
        p = {
            'passing_yards': pass_yds,
            'passing_touchdowns': pass_tds,
            'passing_interceptions': pass_ints,
            'rushing_attempts': rush_att,
            'rushing_yards': rush_yds,
            'rushing_touchdowns': rush_tds,
            'receiving_receptions': rec_recs,
            'receiving_yards': rec_yds,
            'receiving_touchdowns': rec_tds,
        }
        for cat, val in p.items():
            p[cat] = int(val.text)
        pass_c, pass_a = pass_c_a.text.split('/')
        try:
            pass_c = int(pass_c)
            pass_a = int(pass_a)
        except ValueError:
            if pass_c == '-':
                pass_c = None
                pass_a = None
        p.update({
            'passing_completions': pass_c,
            'passing_attempts': pass_a,
        })
        try:
            player = session.query(Player)\
                    .options(eagerload('positions'))\
                    .join(PlayerExternalID)\
                    .filter(PlayerExternalID.external_id==external_id,
                            Player.league_id==1)\
                    .one()
            p['player_id'] = player.id
        except NoResultFound:
            if 'D/ST' in player_info.text:
                continue
            else:
                print player_info.text
                raise Exception('no player found')
        p['projection_id'] = fantasy_proj.id
        if 'pk' not in player.position_string():
            ffp, c = get_or_create(session, FootballOffenseProjection, **p)
    return False
        
def process_pff(data, pos, proj):
    players = data.values()[0]
    base_cats = ['rk', 'player_name', 'team_abbr', 'gp']
    end_cats = ['pts', 'value']
    two_pt = ['two_pt']
    rushing = ['rushing_attempts', 'rushing_yards', 
               'rushing_touchdowns']
    receiving = ['receiving_receptions', 'receiving_yards', 
                 'receiving_touchdowns']
    return_ = ['return_yards', 'return_touchdowns']
    passing = ['passing_completions','passing_attempts', 
               'passing_yards', 'passing_touchdowns', 
               'passing_interceptions', 'passing_sacks',]
    kicking = ['0_19', '20_29', '29_39', '40_49', '50+', 'xp']
    defense = ['rk', 'team_name', 'sacks', 'safeties', 'interceptions', 
                'fumbles_forced', 'fumbles_recovered', 'touchdowns', 
                '0', '1-6', '7-13', '14-20', '21-27', '28-34', '35+', 
                'fantasy_points', 'value']
    fumbles = ['fumbles_total', 'fumbles_lost']
    if pos == 'qb':
        pos_cats = passing + rushing
    elif pos == 'rb':
        pos_cats = rushing + receiving + return_
    elif pos == 'wr':
        pos_cats = receiving + rushing + return_
    elif pos == 'te':
        pos_cats = receiving + return_
    if pos == 'k':
        cats = base_cats + kicking + end_cats
    elif pos == 'dst':
        cats = defense
    else:
        cats = base_cats + pos_cats + fumbles + two_pt + end_cats
    err = ['rk','team_abbr', 'gp', 'pts', 'value']
    for player in players:
        p_dict = dict(zip(cats, player))
        if pos == 'dst':
            team_name = p_dict['team_name'][:-4].rsplit(' ')[-1].lower()
            team = session.query(Team)\
                          .filter(Team.name==team_name)\
                          .one()
            dp = {
                'team_id': team.id,
                'projection_id': proj.id,
            }
            d_cats = ['sacks', 'safeties', 'interceptions', 'fumbles_forced', 
                    'fumbles_recovered', 'touchdowns', 'fantasy_points']
            for cat in d_cats:
                dp.update({cat: int(p_dict[cat])})
            dp, c = get_or_create(session, TeamDefenseProjection, **dp)
        else:
            for k in err:
                p_dict.pop(k)
            player_name = p_dict.pop('player_name').strip()
            if pos == 'k':
                pos = 'pk'
            player_query = session.query(Player)\
                            .join(Person, PersonName)\
                            .join(PlayerPosition, Position)\
                            .filter(Player.league_id==1,
                                    PersonName.full_name==player_name,
                                    Position.abbr==pos)
            try:
                player = player_query.one()
            except NoResultFound:
                pprint(player_name)
                raise Exception('no player')
            except MultipleResultsFound:
                if player_name == 'Chris Givens':
                    player = player_query.all()[0]
                elif player_name == 'Steve Smith':
                    player = session.query(Player).get(1377)
                else:
                    pprint(player_name)
                    raise Exception('asdf')
            p_dict.update({
                'player_id': player.id,
                'projection_id': proj.id
            })
            if pos == 'pk':
                u_19_make, u_19_total = p_dict['0_19'].split('/')
                u_29_make, u_29_total = p_dict['20_29'].split('/')
                u_39_make, u_39_total = p_dict['29_39'].split('/')
                b_40_50_make, b_40_50_total = p_dict['40_49'].split('/')
                o_50_make, o_50_total = p_dict['50+'].split('/')
                xp_make, xp_total = p_dict['xp'].split('/')
                pj = {
                    'u_40_make': (float(u_29_make) + float(u_39_make) 
                                    + float(u_19_make)),
                    'u_40_miss': (float(u_29_total) - float(u_29_make) 
                                    + float(u_39_total) - float(u_39_make)),
                    'b_40_50_make': float(b_40_50_make),
                    'b_40_50_miss': float(b_40_50_total) - float(b_40_50_make),
                    'o_50_make': float(o_50_make),
                    'o_50_miss': float(o_50_total) - float(o_50_make),
                    'xp_make': float(xp_make),
                    'xp_miss': float(xp_total) - float(xp_make),
                    'projection_id': proj.id,
                    'player_id': player.id
                    }
                pk, c = get_or_create(session, FootballKickingProjection, **pj)
            else:
                p, c = get_or_create(session, FootballOffenseProjection, 
                                        **p_dict)

def import_kickers(proj):
    base_url = 'http://games.espn.go.com/ffl/tools/projections?' +\
               'display=alt&slotCategoryId=17&startIndex=%d'
    i = 0
    players = 0
    while players < 32:
        url = base_url % i            
        result = urllib2.urlopen(url)
        body = BeautifulSoup(result)
        pjs = body.findAll('td', text='2013 Projections')
        for p in pjs:
            player = p.findPrevious('a')
            player_id = player['playerid']
            player = session.query(Player)\
                            .join(PlayerExternalID)\
                            .filter(Player.league_id==1,
                                    PlayerExternalID.external_id==player_id)\
                            .one()
            row = p.findPrevious('tr').findAll('td')
            u_40_make, u_40_total = row[2].text.split('/')
            b_40_50_make, b_40_50_total = row[3].text.split('/')
            o_50_make, o_50_total = row[4].text.split('/')
            xp_make, xp_total = row[6].text.split('/')
            pj = {
                'u_40_make': int(u_40_make),
                'u_40_miss': int(u_40_total) - int(u_40_make),
                'b_40_50_make': int(b_40_50_make),
                'b_40_50_miss': int(b_40_50_total) - int(b_40_50_make),
                'o_50_make': int(o_50_make),
                'o_50_miss': int(o_50_total) - int(o_50_make),
                'xp_make': int(xp_make),
                'xp_miss': int(xp_total) - int(xp_total),
                'projection_id': proj.id,
                'player_id': player.id
            }
            pk, c = get_or_create(session, FootballKickingProjection, **pj)
            players += 1
        i += 15
            
def import_defense(proj):
    base_url = 'http://games.espn.go.com/ffl/tools/projections?display=alt&slotCategoryId=16&startIndex=%d'
    i = 0
    players = 0
    while players < 32:
        url = base_url % i            
        result = urllib2.urlopen(url)
        body = BeautifulSoup(result)
        pjs = body.findAll('td', text='2013 Projections')
        for p in pjs:
            team = p.findPrevious('a')
            team_name = team.text[:-5]
            team = session.query(Team)\
                          .filter(Team.name==team_name.lower())\
                          .one()
            row = p.findPrevious('tr').findAll('td')
            players += 1
            dp = {
                'sacks': int(row[2].text),
                'interceptions': int(row[3].text),
                'fumbles_recovered': int(row[4].text),
                'touchdowns': int(row[5].text),
                'points_against': int(row[6].text),
                'yards_against': int(row[7].text),
                'fantasy_points': int(row[9].text),
                'projection_id': proj.id,
                'team_id': team.id
            }
            dp, c = get_or_create(session, TeamDefenseProjection, **dp)
        i += 15
        
def process_cbs(body, pos, proj):
    if pos == 'k':
        pos = 'pk'
    players = body.find('table', attrs={'class':'data'}).findAll('tr')
    players = players[3:-1]
    for p in players:
        rows = p.findAll('td')
        p_info = rows.pop(0)
        p_info = p_info.text.split(',')
        p_name = p_info[0]
        if pos == 'dst':
            team = session.query(Team)\
                          .join(LeagueTeam, League)\
                          .filter(League.id==1,
                                  Team.name==p_name.lower())\
                          .one()                              
        else:
            p_query = session.query(Player)\
                            .join(Person, PersonName, PlayerPosition, 
                                  Position)\
                            .filter(Player.league_id==1, 
                                    PersonName.full_name==p_name,
                                    Position.abbr==pos)
            try:
                player = p_query.one()
            except MultipleResultsFound:
                p_team = p_info[1].split(';')[1].lower()
                player = p_query.join(TeamPlayer, Team)\
                                 .filter(Team.abbr==p_team)\
                                 .one()
            except NoResultFound:
                print p_name
                raise Exception('no player')
        passing = ['passing_attempts', 'passing_completions', 
                'passing_yards', 'passing_touchdowns', 
                'passing_interceptions', 'comp', 'yatt']
        rushing = ['rushing_attempts', 'rushing_yards', 'ravg', 
                'rushing_touchdowns']
        receiving = ['receiving_receptions', 'receiving_yards', 'wavg', 
                    'receiving_touchdowns']
        kicking = ['u_40_make', 'u_40_attempts', 'xp_make']
        fumbles = ['fumbles_lost']
        defense = ['interceptions_z', 'fumbles_recovered', 'fumbles_forced', 
                    'sacks_z', 'touchdowns_z', 'safeties_z', 'points_against', 
                    'yards_against', 'fantasy_points']
        pts = ['pts']
        if pos == 'qb':
            cats = passing + rushing + fumbles
        elif pos == 'rb':
            cats = rushing + receiving + fumbles
        elif pos in ('wr', 'te'):
            cats = receiving + rushing + fumbles
        elif pos == 'pk':
            cats = kicking
        if pos == 'dst':
            cats = defense
        else:
            cats = cats + pts
        p_dict = dict(zip(cats, rows))
        p_dict = {item.replace('_z', ''): float(val.text) 
                    for item, val in p_dict.iteritems() 
                        if '_' in item}
        if pos == 'pk':
            p_dict['u_40_miss'] = p_dict['u_40_attempts'] - p_dict['u_40_make']
            del p_dict['u_40_attempts']
        p_dict['projection_id'] = proj.id
        if pos == 'dst':
            p_dict['team_id'] = team.id
            d, c = get_or_create(session, TeamDefenseProjection, **p_dict)
        else:
            p_dict['player_id'] = player.id
            if pos == 'pk':
                pk, c = get_or_create(session, FootballKickingProjection, 
                                         **p_dict)
            else:
                p, c = get_or_create(session, FootballOffenseProjection, 
                                        **p_dict)
                                        
def process_fftoday(body, pos, proj):
    if pos == 'dst':
        rows = body.findAll('b', text=re.compile('Team'))
    else:
        rows = body.findAll('b', text=re.compile('Player'))
    rows = rows[-1].findPrevious('table').findAll('tr')
    players = rows[2:]
    if not players:
        return True
    for p in players:
        row = p.findAll('td')
        p_info = row.pop(1)
        p_name = p_info.text.split(';')[1]
        if pos == 'dst':
            p_name = p_name.split(' ')[-1]
            team = session.query(Team)\
                          .join(LeagueTeam, League)\
                          .filter(League.id==1,
                                  Team.name==p_name.lower())\
                          .one()             
        else:
            p_query = session.query(Player)\
                            .join(Person, PersonName, PlayerPosition, 
                                  Position)\
                            .filter(Player.league_id==1, 
                                    PersonName.full_name==p_name,
                                    Position.abbr==pos)
            try:
                player = p_query.one()
            except MultipleResultsFound:
                p_team = row[1].text.lower()
                player = p_query.join(TeamPlayer, Team)\
                                 .filter(Team.abbr==p_team)\
                                 .one()
        base = ['cgh', 'team', 'bye']
        passing = ['passing_completions', 'passing_attempts', 'passing_yards', 
                    'passing_touchdowns', 'passing_interceptions']
        rushing = ['rushing_attempts', 'rushing_yards', 'rushing_touchdowns']
        receiving = ['receiving_receptions', 'receiving_yards', 
                        'receiving_touchdowns']
        kicking = ['u_40_make', 'u_40_attempts', 'fgpct', 
                    'xp_make', 'xp_attempts']
        defense = ['cgh', 'bye', 
                    'sacks_z', 'fumbles_recovered', 'interceptions_z', 
                    'touchdowns_z', 'points_against', 'passyds', 'rushyds', 
                    'safeties_z', 'return_td', 'fantasy_points']
        end = ['pts']
        if pos == 'qb':
            cats = passing + rushing
        elif pos == 'rb':
            cats = rushing + receiving
        elif pos == 'wr':
            cats = receiving + rushing
        elif pos == 'te':
            cats = receiving
        elif pos == 'pk':
            cats = kicking
        if pos == 'dst':
            cats = defense
        else:      
            cats = base + cats + end
        p_dict = dict(zip(cats, row))
        p_dict = {item.replace('_z', ''): int(val.text.replace(',', '').replace('.0', ''))
                    for item, val in p_dict.iteritems() 
                        if '_' in item}
        p_dict['projection_id'] = proj.id
        if pos == 'pk':
            p_dict['player_id'] = player.id
            p_dict['u_40_miss'] = p_dict['u_40_attempts'] - p_dict['u_40_make']
            p_dict['xp_miss'] = p_dict['xp_attempts'] - p_dict['xp_make']
            del p_dict['u_40_attempts']
            del p_dict['xp_attempts']
            pk, c = get_or_create(session, FootballKickingProjection, 
                                     **p_dict)
        elif pos == 'dst':
            p_dict['team_id'] = team.id
            p_dict['touchdowns'] += p_dict['return_td']
            del p_dict['return_td']
            q_dict = copy.deepcopy(p_dict)
            del q_dict['fantasy_points']
            d = session.query(TeamDefenseProjection).filter_by(**q_dict).one()
            d.fantasy_points = p_dict['fantasy_points']
            session.add(d)
            session.commit()
            #d, c = get_or_create(session, TeamDefenseProjection, **p_dict)
        else:
            p_dict['player_id'] = player.id
            p, c = get_or_create(session, FootballOffenseProjection, 
                                    **p_dict)
    return False
    
def process_kffl(body, pos, proj):
    if pos == 'dst':
        rows = body.findAll('b', text=re.compile('Team'))
    else:
        rows = body.findAll('b', text=re.compile('Player'))    
    rows = rows[-1].findPrevious('table').findAll('tr')
    if pos == 'pk':
        players = rows[2:]
    else:
        players = rows[1:]
    for p in players:
        row = p.findAll('td')
        p_info = row.pop(2)
        p_name = p_info.text
        if pos == 'dst':
            p_name = p_name.split(' ')[-1]
            team = session.query(Team)\
                          .join(LeagueTeam, League)\
                          .filter(League.id==1,
                                  Team.name==p_name.lower())\
                          .one()             
        else:
            print p_name
            p_query = session.query(Player)\
                            .join(Person, PersonName, PlayerPosition, 
                                  Position)\
                            .filter(Player.league_id==1, 
                                    PersonName.full_name==p_name,
                                    Position.abbr==pos)
            try:
                player = p_query.one()
            except MultipleResultsFound:
                p_team = row[2].text.lower()
                player = p_query.join(TeamPlayer, Team)\
                                 .filter(Team.abbr==p_team)\
                                 .one()
        base = ['rk', 'pos', 'team', 'gp']
        passing = ['passing_completions', 'passing_attempts', 
                    'pass%', 'passing_yards', 
                    'passing_touchdowns', 'passing_interceptions']
        rushing = ['rushing_attempts', 'rushing_yards', 'rushing_touchdowns']
        receiving = ['receiving_receptions', 'receiving_yards', 
                        'receiving_touchdowns']
        kicking = ['1-19_attempts', '1-19_make', 
                    '20-29_attempts', '20-29_make', 
                    '30-39_attempts', '30-39_make', 
                    'b_40_50_attempts', 'b_40_50_make', 
                    'o_50_attempts', 'o_50_make', 'xp_make', 'xp_attempts',  
                    'blocks', 'long', 'fga', 'fgm', 'fg%', 'pts']
        defense = ['rk', 'pos', 'sacks_z', 'interceptions_z', 
                    'fumbles_recovered', 'int_td', 'fumbles_td', 'special_td', 
                    'safeties_z', 'ptd', 'd','fantasy_points']
        end = ['pts']
        fumbles = ['fumbles_lost']
        if pos == 'qb':
            cats = passing + rushing + fumbles + ['passing_sacks']
        elif pos == 'rb':
            cats = rushing + receiving + fumbles + ['receiving_targets', 'touches']
        elif pos == 'wr':
            receiving.insert(1, 'receiving_targets')
            cats = receiving + rushing + fumbles + ['touches']
        elif pos == 'te':
            receiving.insert(1, 'receiving_targets')
            cats = receiving + fumbles
        elif pos == 'pk':
            cats = kicking
        if pos == 'dst':
            cats = defense
        else:
            cats = base + cats + end
        p_dict = dict(zip(cats, row))
        p_dict = {item.replace('_z', ''): int(val.text.replace(',', '').replace('.0', ''))
                    for item, val in p_dict.iteritems() 
                        if '_' in item}
        p_dict['projection_id'] = proj.id
        p_dict['projection_id'] = proj.id
        if pos == 'pk':
            p_dict['player_id'] = player.id
            u_40_attempts = (p_dict['1-19_attempts'] + p_dict['20-29_attempts'] 
                                + p_dict['30-39_attempts'])
            p_dict['u_40_make'] = (p_dict['1-19_make'] + p_dict['20-29_make'] 
                                    + p_dict['30-39_make'])
            p_dict['u_40_miss'] = u_40_attempts - p_dict['u_40_make']
            p_dict['b_40_50_miss'] = (p_dict['b_40_50_attempts'] - 
                                        p_dict['b_40_50_make'])
            p_dict['o_50_miss'] = p_dict['o_50_attempts'] - p_dict['o_50_make']
            p_dict['xp_miss'] = p_dict['xp_attempts'] - p_dict['xp_make']
            remove = ['1-19_attempts', '1-19_make', 
                    '20-29_attempts', '20-29_make', 
                    '30-39_attempts', '30-39_make', 
                    'b_40_50_attempts', 'o_50_attempts', 'xp_attempts']
            for r in remove:
                del p_dict[r]
            pk, c = get_or_create(session, FootballKickingProjection, 
                                     **p_dict)
        elif pos == 'dst':
            p_dict['team_id'] = team.id
            p_dict['touchdowns'] = (p_dict['int_td'] + p_dict['fumbles_td'] + 
                                        p_dict['special_td'])
            remove = ['int_td', 'fumbles_td', 'special_td']
            for r in remove:
                del p_dict[r]
            d, c = get_or_create(session, TeamDefenseProjection, **p_dict)
        else:
            p_dict['player_id'] = player.id
            p, c = get_or_create(session, FootballOffenseProjection, 
                                    **p_dict)
            
        
    
def import_projections(source_name):
    league = session.query(League).get(1)
    season = session.query(Season)\
                    .filter_by(year=2013, league_id=league.id)\
                    .one()
    if not source_name == 'cbs':
        projection = {
            'league_id': league.id,
            'source_name': source_name,
            'season_id': season.id,
        }
        fantasy_proj, c = get_or_create(session, Projection, **projection)
    if source_name == 'espn':
        base_url = 'http://games.espn.go.com/ffl/tools/projections'
        base_url += '?&startIndex=%d'
        finished = False
        i = 0
        while finished == False and i < 400:
            url = base_url % i
            result = urllib2.urlopen(url)
            body = BeautifulSoup(result)
            try:
                finished = process_espn(body, fantasy_proj)
            except ValueError:                
                import_kickers(fantasy_proj)
                import_defense(fantasy_proj)
                return
            i += 40
    elif source_name == 'pff':
        positions = ['qb', 'wr', 'rb', 'te', 'k', 'dst']
        base_url = 'http://www.profootballfocus.com/toolkit/data/1/ROS/%s/' +\
                   '?public=true&_=1372085986943'
        for pos in positions:
            print pos
            url = base_url % pos.upper()
            result = urllib2.urlopen(url)
            data = json.loads(result.read())
            process_pff(data, pos, fantasy_proj)
    elif source_name == 'cbs':
        writer_names = ['Nathan Zegura', 'Jamey Eisenberg', 'Dave Richard']
        for writer_name in writer_names:
            print writer_name
            writer = session.query(Writer)\
                          .join(Person, PersonName)\
                          .filter(PersonName.full_name==writer_name)\
                          .one()
            projection = {
                'league_id': league.id,
                'source_name': source_name,
                'season_id': season.id,
                'writer_id': writer.id
            }
            fantasy_proj, c = get_or_create(session, Projection, **projection)
            positions = ['qb', 'wr', 'rb', 'te', 'k', 'dst']
            base_url = 'http://fantasynews.cbssports.com/fantasyfootball/stats/'
            base_url += 'weeklyprojections/%s/season/%s/?&print_rows=9999'
            for pos in positions:
                print pos
                url = base_url % (pos.upper(), 
                                  writer_name.lower().replace(' ', '_'))
                result = urllib2.urlopen(url)
                body = BeautifulSoup(result)
                process_cbs(body, pos, fantasy_proj)
    elif source_name == 'fftoday':
        base_url = 'http://fftoday.com/rankings/playerproj.php?'
        base_url += 'PosID=%d&LeagueID=1&cur_page=%d'
        pos_dict = {
            'dst': 99,
            'rb': 20,
            'qb': 10,
            'pk': 80,
            'te': 40,
            'wr': 30,
        }
        for pos, num in pos_dict.iteritems():
            print pos
            i = 0
            done = False
            while not done:
                url = base_url % (num, i)
                i += 1
                result = urllib2.urlopen(url)
                body = BeautifulSoup(result)
                done = process_fftoday(body, pos, fantasy_proj)
    elif source_name == 'kffl':
        base_url = 'http://www.kffl.com/a.php/133590/fantasy-football/'
        base_url += 'Fantasy-Football-Rankings--Combination-Scoring/pg%d'
        pos_dict = {
            'qb': 1,
            'rb': 2,
            'wr': 3,
            'te': 4,
            'pk': 5,
            'dst': 6
        }
        for pos, num in pos_dict.iteritems():
            print pos
            url = base_url % num
            result = urllib2.urlopen(url)
            body = BeautifulSoup(result)
            process_kffl(body, pos, fantasy_proj)
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
