import re
import json
import datetime
import urllib, urllib2
from pprint import pprint
from BeautifulSoup import BeautifulSoup
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from helpers import get_team, create_player, get_or_create_player
from connect_db import *
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *

def nba_boxscore(external_id):
    session = create_session()
    league = session.query(League).get(2)
    source_name = 'espn'
    url = 'http://scores.espn.go.com/nba/boxscore?gameId=%s' % external_id
    boxscore = urllib2.urlopen(url)
    body = BeautifulSoup(boxscore)
    game_time = body.find('div', attrs={'class': 'game-time-location'}).p.text
    game_time = datetime.datetime\
                        .strptime(game_time, '%I:%M %p ET, %B %d, %Y')
    #GameTeams
    line_scores = body.find('div', attrs={'class':'line-score-container'})\
                      .findAll('tr')
    teams = line_scores[1], line_scores[2]
    teams = [team.td.text.lower() for team in teams]
    teams = [get_team(session, league, team) for team in teams]
    away_team, home_team = teams
    #Create Game
    game = {
        'game_time': game_time,
        'league': league,
        'away_team': away_team,
        'home_team': home_team
    }
    game, c = get_or_create(session, Game, **game)
    session.commit()
    #Clear everything
    models = [GameTeamScore, BasketballTeamStat, GamePlayer]    
    dnp = session.query(GamePlayerDNP)\
                 .join(GamePlayer, Game)\
                 .filter(Game.id==game.id)
    for d in dnp:
        session.delete(d)
    for model in models:
        deletion = session.query(model).filter_by(game_id=game.id).delete()
    ps = session.query(PlayerStat).filter_by(game_id=game.id)
    for p in ps:
        session.delete(p)
    session.commit()
    #Season
    season = session.query(Season)\
                    .filter(Season.league_id==2, 
                            Season.preseason_start<game_time, 
                            Season.postseason_end>game_time)\
                    .one()
    game.season_id = season.id
    #Game type
    game_date = game_time.date()
    if game_date > season.postseason_start:
        game_type = 'post'
    elif game_date < season.preseason_start:
        game_type = 'pre'
    else:
        game_type = 'reg'
    game.game_type = game_type
    session.add(game)
    session.commit()
    #Game in future
    if game_time > datetime.datetime.now():
        return game
    #Gmae details
    duration = body.find('strong', text=re.compile('Time of Game'))
    if duration:
        duration = duration.parent.next.next.strip()
        duration = datetime.datetime.strptime(duration, '%M:%S').time()
        game.duration = duration    
    network_abbr = body.find('p', text='Coverage: ')
    if network_abbr:
        network_abbr = network_abbr.findNext('strong').text.lower()
        game.network_abbr = network_abbr
    elif 'coverage' in str(body):
        raise Exception('coverage somewhere')
    attendance = body.find('strong', text=re.compile('[A,a]ttendance'))
    if attendance:        
        attendance = attendance.parent.next.next.replace(',', '').strip()
        if not attendance == 'N/A':
            attendance = int(attendance)
            game.attendance = attendance
    elif 'attendance' in str(body):
        raise Exception('attendance somewhere')
    session.add(game)
    session.commit()
    #GameTeamScore
    line_scores = body.find("table", attrs={"class":"linescore"})
    box_scores = line_scores.findAll("td", attrs={"class":"team"})
    for n in range(1,3):
        if n==1:
            game_team = away_team
        else:
            game_team = home_team
        line = box_scores[n].findPrevious("tr").findAll("td")
        periods = len(line)-1
        for period in range(1, periods):
            score = line[period].text.strip()
            try:
                score = int(score)
            except ValueError:
                if score == '':
                    score = None
                else:
                    raise Exception('score is weird')
            team_score = GameTeamScore(game_id=game.id, 
                                       team_id=game_team.id, 
                                       score=score, 
                                       period=period)
            session.add(team_score)
    session.commit()
    #GameTeamStat
    totals = body.findAll('th', text='TOTALS')
    if not totals:
        return game
    team_stat_cats = totals[0].findPrevious('tr').findAll('th')
    team_stat_cats = [str(cat.text) for cat in team_stat_cats]
    team_stat_cat_1 = ['TOTALS', '', 'FGM-A', '3PM-A', 'FTM-A', 'OREB', 
                       'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 
                       '&nbsp;', 'PTS']
    team_stat_cat_2 = ['TOTALS', '', 'FGM-A', '3PM-A', 'FTM-A', 'OREB', 
                       'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 
                       'PTS']
    if not team_stat_cats in [team_stat_cat_1, team_stat_cat_2]:
        raise Exception('unknown team stat header')
    for i, total in enumerate(totals):
        if i == 0:
            team = away_team
        else:
            team = home_team
        stats = total.findNext('tr').findAll('strong')
        if team_stat_cats in [team_stat_cat_1, team_stat_cat_2]:
            if team_stat_cats == team_stat_cat_1:
                team_stat_cat = team_stat_cat_1
            elif team_stat_cats == team_stat_cat_2:
                team_stat_cat = team_stat_cat_2           
            team_stat_cat = team_stat_cat[2:]
            if team_stat_cats == team_stat_cat_1:
                team_stat_cat.pop(-2)
            stats = [stat.text for stat in stats]
            stats = dict(zip(team_stat_cat, stats))
            for cat, stat in stats.items():
                if cat in ['TOTALS', 'OREB', 'DREB', 'REB', 'AST', 'STL', 
                           'BLK', 'TO', 'PF', 'PTS']:
                    stats[cat] = int(stat)
                else:
                    stat = stat.partition('-')
                    made = int(stat[0])
                    attempts = int(stat[2])
                    stats[cat] = (made, attempts)
            ts = {
                'game_id': game.id,
                'team_id': team.id,
                'field_goals_made': stats['FGM-A'][0],
                'field_goals_attempted': stats['FGM-A'][1],
                'threes_made': stats['3PM-A'][0],
                'threes_attempted': stats['3PM-A'][1],
                'free_throws_made': stats['FTM-A'][0],
                'free_throws_attempted': stats['FTM-A'][1],
                'offensive_rebounds': stats['OREB'],
                'defensive_rebounds': stats['DREB'],
                'rebounds': stats['REB'],
                'assists': stats['AST'],
                'steals': stats['STL'],
                'blocks': stats['BLK'],
                'turnovers': stats['TO'],
                'personal_fouls': stats['PF'],
                'points': stats['PTS']
            }
            team_stat = BasketballTeamStat(**ts)
        fast_break_points = total.findNext('strong', 
                                           text=re.compile('Fast break points'))
        if fast_break_points:
            fast_break_points = fast_break_points.next\
                                                 .replace('&nbsp;', '')\
                                                 .strip()
            if not fast_break_points in ('-', 'null'):
                team_stat.fast_break_points = int(fast_break_points)
        paint_points = total.findNext('strong', text=re.compile('Points in the'
                                                                ' paint'))
        if paint_points:
            paint_points = paint_points.next.replace('&nbsp;', '').strip()
            if not paint_points in ('-', 'null'):
                team_stat.paint_points = int(paint_points)
        points_off_turnovers = total.findNext('strong',
                                              text=re.compile('Points off'
                                                              ' turnovers'))
        if points_off_turnovers:
            points_off_turnovers = points_off_turnovers.next\
                                                   .replace('&nbsp;', '')\
                                                   .strip()\
                                                   .partition('(')[2]\
                                                   .partition(')')[0]
            team_stat.points_off_turnovers = int(points_off_turnovers)
        if not points_off_turnovers:
            points_off_turnovers = total.findNext('td',
                                          text=re.compile('Team TO '
                                                          '\(pts off\): '
                                                          '[0-9]{1,2} '
                                                          '\([0-9]{1,2}\)'))
            if points_off_turnovers:
                points_off_turnovers = points_off_turnovers\
                                                .rpartition('(')[2]\
                                                .partition(')')[0]
                team_stat.points_off_turnovers = int(points_off_turnovers)
        session.add(team_stat)
    session.commit()
    #Game Officials  
    officials = body.find('strong', text=re.compile('Officials')).next.strip()
    officials = officials.partition(', ')
    officials = (officials[0],
                officials[2].rpartition(', ')[0], 
                officials[2].rpartition(', ')[2])
    for official_name in officials:
        try:
            official = session.query(Official)\
                              .join(Person, PersonName)\
                              .filter(PersonName.full_name==official_name,
                                      Official.league_id==league.id)\
                              .one()
        except NoResultFound:
            person = Person()
            save(session, person)
            person_name= PersonName(full_name=official_name, 
                                    person_id=person.id)
            save(session, person_name)
            official = Official(person_id=person.id, league_id=league.id)
            save(session, official)
        game_official, created = get_or_create(session, GameOfficial,
                                               game_id=game.id,
                                               official_id=official.id)
    #Player Box Score
    #Starters
    starters_tags = body.findAll("th", text="STARTERS")
    starters = []
    for starter in starters_tags:
        for o in range(5):
            starter = starter.findNext('tr').td
            try:
                starter_name = starter.a.text.replace('  ', ' ')
            except AttributeError:
                starter_name = starter.text.partition(',')[0]
                if starter_name == 'Y Jianlian':
                    starter_name = 'Yi Jianlian'
            starters.append(starter_name)
    if not len(starters) == 10:
        raise Exception('not 10 starters')
    #Player stats
    player_search = r'\bodd player|even player\b'
    players = body.findAll('tr', attrs={'class':re.compile(player_search)})
    stat_cats = starters_tags[0].parent.parent.findAll('th')
    stat_cats = [str(cat.text) for cat in stat_cats]
    stat_cats = stat_cats[1:]
    stat_cats_1 = ['MIN', 'FGM-A', '3PM-A', 'FTM-A', 'OREB', 'DREB', 'REB', 
                   'AST', 'STL', 'BLK', 'TO', 'PF', '+/-', 'PTS']
    stat_cats_2 = ['MIN', 'FGM-A', '3PM-A', 'FTM-A', 'OREB', 'DREB', 'REB', 
                   'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS']
    if not stat_cats in [stat_cats_1, stat_cats_2]:
        raise Exception('unknown box score stat header')
    for player in players:
        stats = player.findAll('td')
        #Team
        team_location = player.findPrevious('tr', 
                                            attrs={'class':'team-color-strip'})\
                              .find('th').a['name'].lower().strip()
        try:
            team = session.query(Team)\
                          .filter(Team.location==team_location,
                                  Team.league==league)\
                          .one()
        except MultipleResultsFound:
            #Usually if Lakers or Clippers
            team_full_name = player.findPrevious('tr', 
                                            attrs={'class':'team-color-strip'})\
                                   .find('th').text.lower()
            team_name = team_full_name.replace(team_location, '').strip()
            team = session.query(Team)\
                          .filter(Team.location==team_location, 
                                  Team.name==team_name)\
                          .filter(Team.league==league)\
                          .one()
        except NoResultFound:
            #For old teams e.g. New jersey nets
            team_full_name = player.findPrevious('tr', 
                                            attrs={'class':'team-color-strip'})\
                                   .find('th').text.lower()
            team_name = team_full_name.replace(team_location, '').strip()
            if team_name == 'supersonics':
                team_name = 'SuperSonics'
            try:
                team = session.query(Team).filter(Team.name==team_name).one()
            except NoResultFound:
                team = session.query(Team)\
                              .join(TeamName)\
                              .filter(Team.league==league,
                                      TeamName.name==team_name)\
                              .one()
        #Create Player
        source_name = 'espn'
        position = False 
        player_link = stats[0]
        try:
            espn_id = player_link.a['href'].partition('/id/')[2]\
                                           .partition('/')[0]
            player_name = player_link.a.text.replace('  ', ' ')
        except TypeError:
            player_link = player_link.text.partition(',')[0].strip()
            if player_link == 'D Carter':
                espn_id = '4324'
                player_name = 'Tweety Carter'
            elif player_link == 'D Noel':
                espn_id='3017'
                player_name = 'David Noel'
            elif player_link == 'Y Jianlian':
                espn_id = '3214'
                player_name = 'Yi Jianlian'
                position = 'pf'
            elif player_link == 'J Richardson':
                position = 'sf'
                player_name = 'Jeremy Richardson'
                espn_id = '3160'
            elif player_link == 'J Williams':
                player_name = 'Justin Williams'
                espn_id = '3052'
                position = 'pf'
            elif (external_id in ['271021030', '271020013', '271018030', 
                                  '271015030', '271013030', '271011001',
                                  '271010019',] 
                              and player_link == 'C Watson'):
                player_name = 'C.J. Watson'
                espn_id = '3277'
                position = 'pg'
            elif player_link == 'J Pinnock':
                player_name = 'J.R. Pinnock'
                espn_id = '3022'
                position = 'g'
            elif player_link == 'J Barea':
                player_name = 'Jose Juan Barea'
                espn_id = '3055'
                position = 'pg'
            elif player_link == 'A Anderson':
                player_name = 'Alan Anderson'
                espn_id = '6569'
                position = 'sg'
            elif player_link == 'L Williams':
                player_name = 'Louis Williams'
                espn_id = '2799'
                position = 'sg'
            elif player_link == 'J White':
                player_name = 'James White'
                espn_id = '3037'
                position = 'sg'
            elif player_link == 'J Hodge':
                player_name = 'Julius Hodge'
                espn_id = '2765'
                position = 'sg'
            elif player_link == 'M Ilic':
                player_name = 'Mile Ilic'
                espn_id = '2766'
                position = 'c'
            elif player_link == 'J Varem':
                player_name = 'Jeff Varem'
                espn_id = '3080'
                position = 'g'
            elif player_link == 'J Davis':
                player_name = 'Josh Davis'
                espn_id = '2212'
                position = 'sf'
            elif player_link == 'C Williams':
                player_name = 'Corey Williams'
                espn_id = '1204'
                source_name = 'rotoworld'
                position = 'g'
            elif player_link == 'E Daniels':
                player_name = 'Erik Daniels'
                espn_id = '2499'
                position = 'f'
            elif player_link == 'M Jones':
                player_name = 'Mark Jones'
                espn_id = '2728'
                position = 'sg'
            elif player_link == 'S Marks':
                player_name = 'Sean Marks'
                espn_id = '511'
                position = 'c'
            elif player_link == 'W Zhi-Zhi':
                player_name = 'ZhiZhi Wang'
                espn_id = '972'
                position = 'c'
            elif player_link == 'M Baker':
                player_name = 'Maurice Baker'
                espn_id = '2706'
                position = 'sg'
            elif player_link == 'K Penney':
                player_name = 'Kirk Penney'
                espn_id = '2189'
                position = 'sg'
            elif player_link == 'B Williams':
                player_name = 'Brandon Williams'
                espn_id = '932'
                position = 'f'
            elif player_link == 'P Drobnjak':
                player_name = 'Predrag Drobnjak'
                espn_id = '212'
                position = 'c'
            elif (external_id in ['261010013']
                              and player_link == 'T Smith'):
                continue
            else:
                pprint(player_link)
                raise Exception('unknown player')
        player_external_id, created = get_or_create(session, 
                                                    PlayerExternalID, 
                                                    external_id=espn_id,
                                                    source_name=source_name,
                                                    league_id=league.id)
        if created:
            player = get_or_create_player(session, league.id, player_name)
            player_external_id.player_id = player.id
            save(session, player_external_id)
        else:
            player = player_external_id.player
        if not player:
            print created
            print player_name
            print espn_id
            raise Exception('no player')
        if not position:
            position = stats[0].text.rpartition(', ')[2].lower()
        try:
            position = session.query(Position)\
                              .filter_by(abbr=position,     
                                         sport_name='basketball')\
                              .one()
        except NoResultFound:           
            if position == 'y jianlian':
                position = 'pf'
            elif position == 'gf':
                position = 'g'
            elif player_name == 'Boniface Napos;Dong':
                position = 'c'
            elif player_name == 'Kenyata Johnson':
                position = 'c'
            elif position == 'fc':
                position = 'c'
            elif player_name == 'Dapos;Or Fischer':
                position = 'c'
            elif position in ['na', 'NA', 'Na']:
                position = None
            else:
                pprint(player_name)
                pprint(position)
                raise Exception('unkown position')
            if position:
                position = session.query(Position)\
                                  .filter_by(abbr=position,     
                                             sport_name='basketball')\
                                  .one()
        if position:
            player_position, c = get_or_create(session, PlayerPosition,
                                               position_id=position.id,
                                               player_id=player.id)
        #Create GamePlayer
        if player_name in starters:
            starter = True
        else:
            starter = False
        gp = {
            'game_id': game.id,
            'player_id': player.id,
            'team_id': team.id,
            'starter': starter,
            'status': 'played'
        }
        game_player = GamePlayer(**gp)
        session.add(game_player)
        session.commit()
        if 'DNP' in str(stats):
            game_player.status = 'dnp'
            save(session, game_player)
            reason = stats[1].text.replace('DNP ', '').strip().lower()
            game_dnp = GamePlayerDNP(id=game_player.id, reason=reason)
            session.add(game_dnp)
            session.commit()
        elif 'NWT JUST SIGNED' in str(stats):
            game_player.status = 'dnp'
            save(session, game_player)
            reason = 'just signed' 
            game_dnp = GamePlayerDNP(id=game_player.id, reason=reason)
            session.add(game_dnp)
            session.commit()
        else:
            if stat_cats in [stat_cats_1, stat_cats_2]:
                if stat_cats == stat_cats_1:
                    stat_cat = stat_cats_1
                elif stat_cats == stat_cats_2:
                    stat_cat = stat_cats_2
                stats = [stat.text for stat in stats[1:]]
                stats = dict(zip(stat_cat, stats))
                for cat, stat in stats.items():
                    if cat in ['MIN', 'OREB', 'DREB', 'REB', 'AST', 'STL', 
                               'BLK', 'TO', 'PF', 'PTS', '+/-']:
                        try:
                            stats[cat] = int(stat)
                        except ValueError:
                            if stat == 'N/A':
                                stats[cat] = None
                            else:
                                raise Exception('something wrong with stat')
                    else:
                        stat = stat.partition('-')
                        made = int(stat[0])
                        attempts = int(stat[2])
                        stats[cat] = (made, attempts)
                gps = {
                    'game_id': game.id,
                    'team_id': team.id,
                    'player_id': player.id,
                    'minutes': stats['MIN'],
                    'field_goals_made': stats['FGM-A'][0],
                    'field_goals_attempted': stats['FGM-A'][1],
                    'threes_made': stats['3PM-A'][0],
                    'threes_attempted': stats['3PM-A'][1],
                    'free_throws_made': stats['FTM-A'][0],
                    'free_throws_attempted': stats['FTM-A'][1],
                    'offensive_rebounds': stats['OREB'],
                    'defensive_rebounds': stats['DREB'],
                    'rebounds': stats['REB'],
                    'assists': stats['AST'],
                    'steals': stats['STL'],
                    'blocks': stats['BLK'],
                    'turnovers': stats['TO'],
                    'personal_fouls': stats['PF'],
                    'points': stats['PTS']
                }
                if stat_cats == stat_cats_1:
                    gps.update({
                        'plus_minus': stats['+/-']
                    })
                game_player_stat = BasketballBoxScoreStat(**gps)
                session.add(game_player_stat)
            session.commit()
    return game        


