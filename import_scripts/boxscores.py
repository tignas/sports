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

session = create_session(True)

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
    
def nfl_boxscore(external_id):
    session = create_session()
    league = session.query(League).filter_by(abbr='nfl').one()
    url = 'http://scores.espn.go.com/nfl/boxscore?gameId=%s' % external_id
    result = urllib2.urlopen(url)
    body = BeautifulSoup(result)
    #Gametime
    game_time = body.find('div', attrs={'class': 'game-time-location'})
    game_time = game_time.p.text
    game_time = datetime.datetime.strptime(game_time, '%I:%M %p ET, %B %d, %Y')
    year = game_time.year
    if game_time.month < 3:
        year -=1
    season = session.query(Season)\
                    .filter_by(league_id=league.id, 
                               year=year)\
                    .one()
                    
    #Teams
    line_scores = body.find('div', attrs={'class':'line-score-container'})\
                      .findAll('tr')
    away_team_abbr = line_scores[1].td.text.lower()
    home_team_abbr = line_scores[2].td.text.lower()
    away_team, home_team = [session.query(Team)\
                                   .filter(Team.league==league, 
                                           Team.abbr==team_abbr)\
                                   .one()
                            for team_abbr in [away_team_abbr, home_team_abbr]]
    #Retrieve game
    game = {
        'game_time': game_time,
        'home_team': home_team,
        'away_team': away_team,
        'season': season,
        'league': league
    }
    game, c = get_or_create(session, Game, **game)
    #Clear Game
    models = [GameTeamScore, FootballTeamStat, GamePlayer] 
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
    #Game details
    network = body.find('p', text='Coverage: ')
    if network:
        network.findNext('strong').text.lower()
        network, created = get_or_create(session, Network, abbr=network)
        game.network_abbr = network.abbr
    attendance = body.find('span', text='Attendance:')
    if attendance:
        attendance = attendance.parent.\
                        findPrevious('div').text.\
                        partition(':')[2].replace(',', '').strip()
        try:
            game.attendance = int(attendance)
        except ValueError:
            if attendance == 'NA':
                pass
            else:
                print attendance
                raise Exception('something wrong with attendance')
    else:
        raise Exception('no attendance')
    session.add(game)
    session.commit()
    #Team stats
    team_stats = body.find('h4', text='Team Stat Comparison')\
                     .findNext('div')\
                     .find('table')\
                     .find('tbody')\
                     .findAll('tr')
    ts = session.query(FootballTeamStat)\
                .filter_by(game_id=game.id)\
                .delete()
    session.commit()
    home_team_stat = FootballTeamStat(game_id=game.id, team_id=home_team.id)
    away_team_stat = FootballTeamStat(game_id=game.id, team_id=away_team.id)
    for row in team_stats:
        items = row.findAll('td')
        category = items[0].text.lower()
        for num, team_stat in enumerate([away_team_stat, home_team_stat]):
            stat = items[num+1].text
            if category == 'passing 1st downs':
                team_stat.passing_first_downs = int(stat)
            elif category == 'rushing 1st downs':
                team_stat.rushing_first_downs = int(stat)
            elif category == '1st downs from penalties':
                team_stat.penalty_first_downs = int(stat)
            elif category == '3rd down efficiency':
                stat = stat.partition('-')
                team_stat.third_down_conversions = int(stat[0])
                team_stat.third_down_attempts = int(stat[2])
            elif category == '4th down efficiency':
                stat = stat.partition('-')
                team_stat.fourth_down_conversions = int(stat[0])
                team_stat.fourth_down_attempts = int(stat[2])
            elif category == 'total plays':
                team_stat.plays = int(stat)
            elif category == 'total yards':
                team_stat.yards = int(stat)
            elif category == 'total drives':
                try:
                    team_stat.drives = int(stat)
                except ValueError:
                    if stat == '-':
                        team_stat.drives = None
                    else:
                        pprint(drive)
                        raise Exception('uknown stat')
            elif category == 'passing':
                team_stat.passing_yards = int(stat)
            elif category == 'comp - att':
                stat = stat.partition('-')
                team_stat.passing_completions = int(stat[0])
                team_stat.passing_attempts = int(stat[2])
            elif category == 'interceptions thrown':
                team_stat.interceptions = int(stat)
            elif category == 'sacks - yards lost':
                stat = stat.partition('-')
                team_stat.sack_total = int(stat[0])
                team_stat.sack_yards = int(stat[2])
            elif category == 'rushing':
                team_stat.rushing_yards = int(stat)
            elif category == 'rushing attempts':
                team_stat.rushing_attempts = int(stat)
            elif category == 'red zone (made-att)':
                stat = stat.partition('-')
                team_stat.red_zone_conversions = int(stat[0])
                team_stat.red_zone_attempts = int(stat[2])
            elif category == 'penalties':
                stat = stat.partition('-')
                team_stat.penalty_total = int(stat[0])
                team_stat.peanlty_yards = int(stat[2])
            elif category == 'turnovers':
                team_stat.fumbles_lost = int(stat)
            elif category == 'defensive / special teams tds':
                try:
                    stat = int(stat)
                    team_stat.defensive_special_teams_tds = int(stat)
                except ValueError:
                    if not stat == '-':
                        raise Exception('something wrong here')
            elif category == 'possession':
                stat = stat.partition(':')
                minute, a, second = stat
                time_of_possession = datetime.time(minute=int(minute), 
                                                    second=int(second))
                team_stat.time_of_possession = time_of_possession
            session.add(team_stat)
    session.commit()
    #Game Team Scores
    for num, line in enumerate(line_scores):
        if not num == 0:
            scores = line.findAll('td')
            for period, score in enumerate(scores):
                if num == 1:
                    team = away_team
                else:
                    team = home_team
                if not period == 0 and not period == (len(scores)-1):
                    try:
                        score = int(score.text)
                        game_team_score = GameTeamScore(game_id=game.id, 
                                                        team_id=team.id, 
                                                        score=score, 
                                                        period=period)
                        session.add(game_team_score)
                    except ValueError:
                        if external_id.external_id == '270825028':
                            continue
                        else:
                            raise Exception('missing score')
    session.commit()
    #Player Stats
    stat_cats = ['Tackles', 'Interceptions', 'Passing', 'Rushing', 
                'Receiving', 'Fumbles', 'Defensive', 'Kick Returns', 
                'Punt Returns', 'Kicking', 'Punting']
    for stat in stat_cats:
        search = " %s" % stat
        tables = body.findAll('th', text=re.compile(search))
        for table in tables:
            headers = table.findPrevious('thead').findNext('tr').\
                                findNext('tr').findAll('th')
            header = []
            for head in headers:
                header.append(head.text)
            #Find correct team associated to stat
            team_name = table.replace(stat, '').strip().lower()
            team = session.query(Team).filter_by(location=team_name).first()
            if not team:
                team = session.query(Team).filter_by(abbr=team_name).first()
            if not team:
                short_name = team_name.rpartition(' ')[2]
                team = session.query(Team).filter_by(name=short_name).first()
            if not team:
                if table in ['T. Rushing', 
                        'Tj Rushing 90 Yd Punt Return (Adam Vinatieri Kick) ']:
                    continue
                else:
                    raise Exception('fuck this shit %s' % team_name)
            #Select all players for the stat
            try:
                players = table.findPrevious('table').tbody.findAll('tr')
            except AttributeError:
                if stat == 'Punting':
                    players = table.findPrevious('table').findAll('tr')
                    players = players[2:-1]
                else:
                    print table
                    raise Exception('cant find table')
            for player in players:
                stats = player.findAll('td')
                try:
                    player_link = stats[0].a['href']
                    invalid = False
                except TypeError:
                    player_link, invalid = player_exceptions(stats, external_id.external_id)
                if not invalid:
                    espn_id = re.search(r'/(?P<espn_id>[0-9]+)/', player_link)
                    espn_id = espn_id.groupdict()['espn_id']
                    player_id, created = get_or_create(session, PlayerExternalID,
                                        external_id=espn_id, source_name='espn',
                                        league_id=league.id)
                    if created:
                        person = save(session, Person())
                        player = Player(person_id=person.id, 
                                        league_id=league.id)
                        player = save(session, player)
                        full_name = player_link.rpartition('/')[2].\
                                                replace('-', ' ').title()
                        name = get_or_create(session, PersonName, 
                                            full_name=full_name, 
                                            person_id=person.id)
                        player_id.player_id = player.id
                        save(session, player_id)
                    player = player_id.player
                elif player_link:
                    full_name = player_link
                    name, created = get_or_create(session, PersonName, 
                                        full_name=full_name) 
                    if created:
                        person = save(session, Person())
                        player = Player(person_id=person.id, 
                                        league_id=league.id) 
                        player = save(session, player)
                        name.person_id = person.id
                        save(session, player)
                    invalid = True                    
                if not invalid:
                    team_players = session.query(TeamPlayer)\
                                         .filter_by(team_id=team.id, 
                                                    player_id=player.id)\
                                         .all()
                    if len(team_players) > 1:
                        team_player = team_players[0]
                        delete(team_players[1])
                    elif len(team_players) == 1:
                        team_player = team_players[0]
                    else:
                        team_player = session.add(TeamPlayer(team_id=team.id, player_id=player.id))
                        session.commit()
                    game_player = GamePlayer(game=game, 
                                             team=team,
                                             player=player)
                if invalid:
                    pass
                elif stat == 'Passing':
                    player_stat = passing_stat(session, header, 
                                               stats, game, player, team)
                elif stat == 'Rushing':
                    player_stat = rushing_stat(session, header, 
                                               stats, game, player, team)
                elif stat == 'Receiving':
                    player_stat = receiving_stat(session, header, 
                                                 stats, game, player, team)
                elif stat == 'Fumbles':
                    player_stat = fumble_stat(session, header,
                                              stats, game, player, team)
                elif stat == 'Defensive' or stat == 'Tackles':
                    headers = stats[0].findPrevious('thead')\
                                      .findNext('tr')\
                                      .findNext('tr')\
                                      .findNext('tr')\
                                      .findAll('th')
                    defensive_header = []
                    for head in headers:
                        defensive_header.append(head.text)
                    player_stat = defensive_stat(session, defensive_header,
                                                 header, stats, game, player, team)
                elif stat == 'Kick Returns' or stat == 'Punt Returns':
                    return_type = 'kick' if stat == 'Kick Returns' else 'punt'
                    player_stat = return_stat(session, header,
                                              stats, game, player, team,
                                              return_type)
                elif stat == 'Kicking':
                    player_stat = kicking_stat(session, header,
                                               stats, game, player, team)
                elif stat == 'Punting':
                    player_stat = punting_stat(session, header,
                                               stats, game, player, team)
                elif stat == 'Interceptions':
                    player_stat = interception_stat(session, header,
                                                    stats, game, player, team)
                else:
                    print header
                    raise Exception('unknown header what to do?')
    return game
          
def passing_stat(session, header, stats, game, player, team):
    passing_header_1 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 'INT', 'RAT.']
    passing_header_2 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 'INT']
    passing_header_3 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 
                        'INT', 'SACKS', 'QBR', 'RTG']
    passing_header_4 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 'INT', 
                        'SACKS', 'RTG']
    passing_header_5 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 'INT', 
                        'SACKS', 'QBR']
    passing_header_6 = ['&nbsp;', 'C/ATT', 'YDS', 'AVG', 'TD', 'INT', 'SACKS']

    if header in [passing_header_1, passing_header_2, passing_header_3, 
                    passing_header_4, passing_header_5, passing_header_6]:
        c_att = stats[1].text.partition('/')
        completions = int(c_att[0])
        attempts = int(c_att[2])
        yards = int(stats[2].text)
        touchdowns = int(stats[4].text)
        interceptions = int(stats[5].text)
        if header in [passing_header_3, passing_header_4, 
                        passing_header_5, passing_header_6]:
            sacks, p, sack_yards = stats[6].text.partition('-')
            sacks = int(sacks)
            sack_yards = int(sack_yards)
            passing_stat, created = get_or_create(session, FootballPassingStat,
                                    game_id=game.id,
                                    player_id=player.id,
                                    team_id=team.id,
                                    attempts=attempts, 
                                    completions=completions,
                                    yards=yards, touchdowns=touchdowns,
                                    interceptions=interceptions, sacks=sacks,
                                    sack_yards=sack_yards)
        else:
            passing_stat, created = get_or_create(session, FootballPassingStat,
                                game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                completions=completions, yards=yards, 
                                touchdowns=touchdowns, attempts=attempts,
                                interceptions=interceptions)                   
    else:
        print header
        raise Exception('passing unknown header')

def rushing_stat(session, header, stats, game, player, team):
    rushing_header_1 = ['&nbsp;', 'CAR', 'YDS', 'AVG', 'TD', 'LG']
    if header == rushing_header_1:
        attempts = int(stats[1].text)
        yards = int(stats[2].text)
        touchdowns = int(stats[4].text)
        longest = int(stats[5].text)
        rushing_stat, created = get_or_create(session, FootballRushingStat,
                                game_id=game.id,
                                player_id=player.id,
                                    team_id=team.id,
                                attempts=attempts, yards=yards, 
                                touchdowns=touchdowns, longest=longest)
    else:        
        b = stats[0]
        print b
        raise Exception('rushing uknown header')

def receiving_stat(session, header, stats, game, player, team):
    receiving_header_1 = ['&nbsp;', 'REC', 'YDS', 'AVG', 'TD', 'LG', 'TGTS']
    receiving_header_2 = ['&nbsp;', 'REC', 'YDS', 'AVG', 'TD', 'LG']
    if header == receiving_header_1:
        receptions = int(stats[1].text)
        yards = int(stats[2].text)
        touchdowns = int(stats[4].text)
        longest = int(stats[5].text)
        try:
            targets = int(stats[6].text)
        except ValueError:
            if stats[6].text == '-':
                targets = 0
            else:
                raise Exception('unknown target receptions character')
        receiving_stat, created = get_or_create(session, FootballReceivingStat,
                                    game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                    targets=targets, receptions=receptions, 
                                    yards=yards, touchdowns=touchdowns, 
                                    longest=longest)
    elif header == receiving_header_2:
        receptions = int(stats[1].text)
        yards = int(stats[2].text)
        touchdowns = int(stats[4].text)
        longest = int(stats[5].text)
        receiving_stat, created = get_or_create(session, FootballReceivingStat,
                                    game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                    longest=longest, touchdowns=touchdowns,
                                    receptions=receptions, yards=yards)
    else:
        raise Exception('receiving unknown header')
        
def fumble_stat(session, header, stats, game, player, team):
    fumble_header_1 = ['&nbsp;', 'FUM', 'LOST', 'REC']
    if header == fumble_header_1:
        fumbles = int(stats[1].text)
        lost = int(stats[2].text)
        recovered = int(stats[3].text)
        fumble_stat, created = get_or_create(session, FootballFumbleStat,
                                            game_id=game.id,
                                            player_id=player.id, 
                                    team_id=team.id,
                                            fumbles=fumbles, lost=lost, 
                                            recovered=recovered)
    else:
        fumble_header_1 = ['&nbsp;', 'FUM', 'LOST', 'REC']
        raise Exception('fumble unknown header')
        
def defensive_stat(session, defensive_header, header, stats, game, player, team):
    defensive_header_1 = ['&nbsp;', 'TOT', 'SOLO', 'SACKS', 
                            'TFL', 'PD', 'QB HTS', 'TD']
    defensive_header_2 = ['&nbsp;', 'TOT', 'SACKS', 'SOLO']
    if defensive_header == defensive_header_1:
        tackles = int(stats[1].text)
        solo = int(stats[2].text)
        sacks = float(stats[3].text)
        tackles_for_loss = int(stats[4].text)
        pass_deflections = int(stats[5].text)
        qb_hits = int(stats[6].text)
        touchdowns = int(stats[7].text)
        defensive_stat, created = get_or_create(session, FootballDefensiveStat,
                                        game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                        tackles=tackles, solo=solo, 
                                        sacks=sacks, qb_hits=qb_hits,
                                        tackles_for_loss=tackles_for_loss,
                                        pass_deflections=pass_deflections, 
                                        touchdowns=touchdowns)
    elif header == defensive_header_2:
        tackles = int(stats[1].text)
        sacks = float(stats[2].text)
        solo = int(stats[3].text)
        defensive_stat, created = get_or_create(session, FootballDefensiveStat,
                                        game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                        tackles=tackles, solo=solo, 
                                        sacks=sacks)
    else:
        raise Exception('unknown defensive header')
        
def return_stat(session, header, stats, game, player, team, return_type):
    return_header_1 = ['&nbsp;', 'NO', 'YDS', 'AVG', 'LG', 'TD']
    return_header_2 = ['&nbsp;', 'NO', 'YDS', 'AVG', 'TD']
    return_header_3 = ['&nbsp;', 'NO', 'YDS', 'AVG', 'LG']
    if header in [return_header_1, return_header_2, return_header_3]:
        total = int(stats[1].text)
        yards = int(stats[2].text)
    else:
        raise Exception('where my return stats at?')
    if header == return_header_1:
        longest = int(stats[4].text)
        touchdowns = int(stats[5].text)
        return_stat, created = get_or_create(session, FootballReturnStat,
                                        game_id=game.id, player_id=player.id,
                                        team_id=team.id,
                                        total=total, yards=yards, 
                                        longest=longest, touchdowns=touchdowns,
                                        return_type=return_type)
    elif header == return_header_2:
        touchdowns = int(stats[4].text)
        return_stat, created = get_or_create(session, FootballReturnStat,
                                        game_id=game.id, player_id=player.id,
                                        team_id=team.id,
                                        total=total, yards=yards, 
                                        touchdowns=touchdowns, 
                                        return_type=return_type)
    elif header == return_header_3:
        longest = int(stats[4].text)
        return_stat, created = get_or_create(session, FootballReturnStat,
                                        game_id=game.id, player_id=player.id,
                                        team_id=team.id,
                                        total=total, yards=yards, 
                                        longest=longest, 
                                        return_type=return_type)
                                        
def kicking_stat(session, header, stats, game, player, team):
    kicking_header_1 = ['&nbsp;', 'FG', 'PCT', 'LONG', 'XP', 'PTS']
    kicking_header_2 = ['&nbsp;', 'FG', 'PCT', 'XP', 'PTS']
    if header == kicking_header_1:
        fgs = stats[1].text.partition('/')
        fg_made = int(fgs[0])
        fg_attempts = int(fgs[2])
        longest = stats[3].text
        longest = 0  if longest == '--' else int(longest)
        xps = stats[4].text.partition('/')
        xp_made = int(xps[0])
        xp_attempts = int(xps[2])
        kicking_stat, created = get_or_create(session, FootballKickingStat,
                                            game_id=game.id,
                                            player_id=player.id,
                                    team_id=team.id,
                                            fg_made=fg_made, 
                                            fg_attempts=fg_attempts,
                                            longest=longest, xp_made=xp_made,
                                            xp_attempts=xp_attempts)
    elif header == kicking_header_2:
        fgs = stats[1].text.partition('/')
        fg_made = int(fgs[0])
        fg_attempts = int(fgs[2])
        xps = stats[3].text.partition('/')
        xp_made = int(xps[0])
        xp_attempts = int(xps[2])
        kicking_stat, created =  get_or_create(session, FootballKickingStat,
                                            game_id=game.id,
                                            player_id=player.id,
                                    team_id=team.id,
                                            fg_made=fg_made, 
                                            fg_attempts=fg_attempts,
                                            xp_made=xp_made,
                                            xp_attempts=xp_attempts)
    else:
        raise Exception('unkown kicking header')
        
def punting_stat(session, header, stats, game, player, team):
    punting_header_1 = ['&nbsp;', 'TOT', 'YDS', 'AVG', 'TB', '-20', 'LG']
    punting_header_2 = ['&nbsp;', 'NO', 'YDS', 'AVG']
    if header == punting_header_1:
        total = int(stats[1].text)
        yards = int(stats[2].text)
        touchbacks = int(stats[4].text)
        inside_20 = int(stats[5].text)
        longest = int(stats[6].text)
        punting_stat, created = get_or_create(session, FootballPuntingStat,
                                        game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                        total=total, yards=yards, 
                                        touchbacks=touchbacks,
                                        inside_20=inside_20, longest=longest)
    elif header == punting_header_2:
        total = int(stats[1].text)
        yards = int(stats[2].text)
        punting_stat, created = get_or_create(session, FootballPuntingStat,
                                            game_id=game.id, player_id=player.id,
                                    team_id=team.id,
                                            total=total, yards=yards)
    else:
        raise Exception('unknown punting header')
        
def interception_stat(session, header, stats, game, player, team):
    interception_header_1 = ['&nbsp;', 'INT', 'YDS', 'TD']
    if header == interception_header_1:
        total = int(stats[1].text)
        yards = int(stats[2].text)
        touchdowns = int(stats[3].text)
        interception_stat, c = get_or_create(session, FootballInterceptionStat,
                                            total=total, yards=yards, 
                                            touchdowns=touchdowns,
                                            game_id=game.id,
                                            player_id=player.id,
                                            team_id=team.id)

def player_exceptions(stats, id_num):
    invalid = False
    player_link = None
    id_num = int(id_num)
    if stats[0].text == '-. Team':
        invalid = True
    elif stats[0].text == 'J. Walton' and id_num in [310918007, 301114007]:
        player_link = 'nfl/player/_/id/13303/jd-walton'
    elif stats[0].text == 'T. Johnson':
        player_link = 'nfl/player/stats/_/id/10001/tom-johnson'
    elif stats[0].text == 'W. Smith' and id_num == 320101021: 
        player_link = 'nfl/player/stats/_/id/10001/tom-johnson'
    elif stats[0].text == 'H. Hynoski':
        player_link = 'nfl/player/_/id/14608/henry-hynoski'
    elif stats[0].text == 'S. Siliga':
        player_link = '/nfl/player/_/id/14441/sealver-siliga'
    elif stats[0].text == 'C. Johnson' and id_num in [310901003, 310827010, 
                                                      310822019]:
        player_link = '/nfl/player/stats/_/id/13879/chris-johnson'
    elif stats[0].text == 'M. Johnson' and id_num in [310827008, 310819005, 
                                                      310812008]:
        player_link = 'nfl/player/stats/_/id/10667/michael-johnson'
    elif stats[0].text == 'A. Jackson' and id_num == 310827023:
        player_link = '/nfl/player/_/id/14207/andrew-jackson'
    elif stats[0].text == 'B. Taylor' and id_num == 310821006:
        player_link = '/nfl/player/_/id/14350/brandon-taylor'
    elif stats[0].text == 'A. Leon' and id_num == 310811021:
        player_link = '/nfl/player/stats/_/id/14607/anthony-leon'
    elif stats[0].text == 'E. Fowler' and id_num in [290815008, 300828008]:
        player_link = 'nfl/player/stats/_/id/11213/eric-fowler'
    elif stats[0].text == 'M. Spurlock':
        player_link = 'nfl/player/_/id/10327/micheal-spurlock'
    elif stats[0].text == 'D. Wright' and id_num in [290903017, 290829019, 
                                                     290817019]:
        player_link = 'nfl/player/stats/_/id/12751/deandre-wright'
    elif stats[0].text == 'S. Williams' and id_num in [290828028, 290903017, 
                                                       290820017, 290813021]:
        player_link = '/nfl/player/stats/_/id/10365/steve-williams'
    elif stats[0].text == 'V. Haynes' and id_num in [271230033,290829001]:
        player_link = '/nfl/player/stats/_/id/3695/verron-haynes'
    elif stats[0].text == 'B. Miller' and id_num == 281221026:
        player_link = '/nfl/player/stats/_/id/2441/brandon-miller'
    elif stats[0].text == 'E. Bassey':
        player_link = '/nfl/player/stats/_/id/9861/eric-bassey'
    elif stats[0].text == 'W. Heller' and id_num in [280825024, 281012026, 
                                                     280907002]:
        player_link = '/nfl/player/_/id/4972/will-heller'
    elif stats[0].text == 'J. Bradley' and id_num in [280809029,280824011, 
                                                      280828011]:
        player_link = '/nfl/player/stats/_/id/10771/joe-bradley'
    elif stats[0].text == 'T. Holt' and id_num in [280809029,280823029, 
                                                   280828023]:
        player_link = '/nfl/player/stats/_/id/4595/terrence-holt'
    elif stats[0].text == 'B. Moore':
        player_link = '/nfl/player/stats/_/id/4353/brandon-moore'
    elif stats[0].text == 'M. Prater':
        player_link = '/nfl/player/stats/_/id/11122/matt-prater'
    elif stats[0].text == 'D. Johnson' and id_num == 270916003:
        player_link = '/nfl/player/stats/_/id/4341/dirk-johnson'
    elif stats[0].text == 'T. Perry':
        player_link = '/nfl/player/stats/_/id/8604/tab-perry'
    elif stats[0].text == 'C. Johnson' and id_num in [270817020,270830016]:
        player_link = '/nfl/player/stats/_/id/10918/chad-johnson'
    elif stats[0].text == 'J. Landrom':
        player_link = '/nfl/player/gamelog/_/id/10421/jamar-landrom'
    elif stats[0].text == 'C. Ah You':
        player_link = '/nfl/player/stats/_/id/10682/cj-ah-you'
    elif stats[0].text == 'K. Smith' and id_num == 270825026:
        player_link = '/nfl/player/gamelog/_/id/9774/kurt-smith'
    elif stats[0].text == 'J. Porter' and id_num in [270805023, 270810018, 
                                                     270818004]:
        player_link = '/nfl/player/stats/_/id/10711/joe-porter'
    elif stats[0].text == 'J. Vaughn' and id_num in  [270811010, 270817017, 
                                                      270824002]:
        player_link = '/nfl/player/stats/_/id/12251/john-vaughn'
    elif stats[0].text == 'K. Gonzalez' and id_num == 270816012:
        player_link = '/nfl/player/stats/_/id/10701/kiki-gonzalez'
    elif stats[0].text == 'R. Alexis' and team.name == 'Jaguars':
        player_link = '/nfl/player/stats/_/id/6300/rich-alexis'
    elif stats[0].text == 'J. Farris' and id_num in [260114026, 260831028, 
                                                     270811015]:
        player_link = '/nfl/player/gamelog/_/id/3526/jimmy-farris'
    elif stats[0].text == 'T. Faulk' and id_num == 270805023:
        player_link = '/nfl/player/stats/_/id/4422/trev-faulk'
    elif stats[0].text == 'S. Dequincy' and id_num == 261112010:
        player_link = '/nfl/player/stats/_/id/4286/dequincy-scott'
    elif stats[0].text == 'J. Cooper' and id_num in [260818002, 260826002]:
        player_link = '/nfl/player/stats/_/id/6133/josh-cooper'
    elif stats[0].text == 'S. Mitchell' and id_num in [260812015, 260824029]:
        player_link = '/nfl/player/stats/_/id/9378/shirdonya-mitchell'
    elif stats[0].text == 'X. Beitia':
        player_link = '/nfl/player/stats/_/id/10150/xavier-beitia'
    elif stats[0].text == 'J. Goddard' and id_num in [250812020, 260101011, 
                                                      260810014]:
        player_link = '/nfl/player/stats/_/id/8620/johnathan-goddard'
    elif stats[0].text == 'J. Browning' and team.name == 'Chiefs':
        player_link = '/nfl/player/stats/_/id/1030/john-browning'
    elif stats[0].text == 'W. Green' and id_num == 250925011:
        player_link = '/nfl/player/_/id/3544/william-green'
    elif stats[0].text == 'M. Smith' and id_num == 250902014:
        player_link = '/nfl/player/stats/_/id/9459/mckenzi-smith'
    elif stats[0].text == 'S. Williams' and id_num == 310811017:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                      '10365/steve-williams'
    elif stats[0].text == 'A. Davis' and id_num == 290831034:
        player_link = 'http://espn.go.com/nfl/player/_/id/3575/andre-davis'
    elif stats[0].text == 'B. Robinson' and id_num == 280807022:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                      '1349/bryan-robinson'
    elif stats[0].text == 'K. Smith' and id_num == 270812024:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                       '9774/kurt-smith'
    elif stats[0].text == 'M. Erickson' and id_num == 260812010:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                      '10176/mike-erickson'
    elif stats[0].text == 'M. Grant' and id_num == 250901003:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                      '11878/michael-grant'
    elif stats[0].text == 'C. Stovall' and id_num == 250901021:
        player_link = 'Chauncey Stovall'
        invalid = True
    elif stats[0].text == 'C. Perez' and id_num in [250815023, 250820033, 
                                                    250901021]:
        player_link = 'Carlos Perez'
    elif stats[0].text == 'S. Savoy' and id_num in [250812020,250829008]:
        player_link = 'Steve Savoy'
    elif stats[0].text == 'G. Adams' and id_num == 250815023:
        player_link = 'Grant Adams'
    elif stats[0].text == 'R. Killeen' and id_num == 250829008:
        player_link = 'Ryan Killeen'
    elif stats[0].text == 'E. Thompson' and id_num in [250812016,250827012]:
        player_link = 'Edwin Thomson'
    elif stats[0].text == 'G. Cook' and id_num in [250813025, 250820034, 
                                                   250826013]:
        player_link = 'Gary Cook'
    elif stats[0].text == 'M. Washington' and id_num == 250826013:
        player_link = 'Maurice Washington'
    elif stats[0].text == 'T. Jones' and id_num in [250813005, 250820008, 
                                                    250826005]:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/10198/tyler-jones'
    elif stats[0].text == 'G. Franklin' and id_num == 250811009:
        player_link = 'http://espn.go.com/nfl/players/profile?playerId=9474'
    elif stats[0].text == 'N. Fiske' and id_num in [250812018, 250818017]:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/4925/nate-fikse'
    elif stats[0].text == 'S. Burley' and id_num == 250812016:
        player_link = 'Siaha Burley'
    elif stats[0].text == 'D. Reid' and id_num == 250826016:
        player_link = 'Duncan Reid'
    elif stats[0].text == 'G. Guidugli' and id_num == 250812010:
        player_link = 'Gino Guidugli'
    elif stats[0].text == 'J. Ohliger' and id_num == 250813001:
        player_link = 'Jesse Ohliger'
    elif stats[0].text == 'D. Young' and id_num == 250826016:
        player_link = 'Danny Young'
    elif stats[0].text == 'L. Anderson' and id_num == 250826021:
        player_link = 'Lyonel Anderson'
    elif stats[0].text == 'C. Friehauf' and id_num == 250820007:
        player_link = 'Chad Friehauf'
    elif stats[0].text == 'T. Ficklin' and id_num == 250820007:
        player_link = 'Tony Ficklin'
    elif stats[0].text == 'B. Benekos' and id_num == 250820034:
        player_link = 'Bryce Benekos'
    elif stats[0].text == 'J. Kibble' and id_num == 250820033:
        player_link = 'Jimmy Kibble'
    elif stats[0].text == 'W. Peoples' and id_num == 250820002:
        player_link = 'Will Peoples'
    elif stats[0].text == 'H. Jackson' and id_num == 250820008:
        player_link = 'Howard Jackson'
    elif stats[0].text == 'A. Nwabuisi' and id_num in [250812020, 250819020]:
        player_link = 'Austine Nwabuisi'
    elif stats[0].text == 'B. Ralph' and id_num == 250819020:
        player_link = 'Brock Ralph'
    elif stats[0].text == 'R. Dinwiddie' and id_num == 250808015:
        player_link = 'Ryan Dinwiddie'
    elif stats[0].text == 'W. Reyes' and id_num in [250812010, 250819001]:
        player_link = 'Walter Reyes'
    elif stats[0].text == 'Q. Newhouse' and id_num == 250811009:
        player_link = 'Quintene Newhouse'
    elif stats[0].text == 'M. Tant' and id_num == 250811009:
        player_link = 'Matthew Tant'
    elif stats[0].text == 'A. Nix' and id_num == 250819001:
        player_link = 'Alonzo Nix'
    elif stats[0].text == 'C. Sullivan' and id_num == 250812004:
        invalid = True
    elif stats[0].text == 'V. Cartwright' and id_num == 250819001:
        player_link = 'Vince Cartwright'
    elif stats[0].text == 'E. Johnson' and id_num == 250819001:
        player_link = 'Earvin Johnson'
    elif stats[0].text == 'J. Bowenkamp' and id_num == 250812016:
        player_link = 'John Bowenkamp'
    elif stats[0].text == 'D. Pitts' and id_num == 250813034:
        player_link = 'Devin Pitts'
    elif stats[0].text == 'R. Kopp' and id_num in [250812004, 250818017]:
        player_link = 'Rhett Kopp'
    elif stats[0].text == 'J. Jones' and id_num == 250815023:
        player_link = 'Jared Jones'
    elif stats[0].text == 'D. Zeigler' and id_num == 250813025:
        player_link = 'Doug Zeigler'
    elif stats[0].text == 'A. Guman' and id_num == 250812020:
        player_link = 'Andrew Guman'
    elif stats[0].text == 'C. Cox' and id_num == 250812020:
        player_link = 'Chip Cox'
    elif stats[0].text == 'E. Mahl' and id_num == 250812020:
        player_link = 'Eric Mahl'
    elif stats[0].text == 'H. Jackson' and id_num == 250812020:
        player_link = 'Howard Jackson'
    elif stats[0].text == 'C. Newton' and id_num in [260811001, 260819009,
                                                     260831001, 270811019, 
                                                     270824029, 270830029,
                                                     270830029]:
        player_link = 'Cameron Lamark Newton'
        invalid = True
    elif stats[0].text == 'D. Curry' and id_num == 250902004:
        player_link = 'Derek Curry'
    elif stats[0].text == 'C. Scates' and id_num in [250813034, 250820034, 
                                                     250827006, 250901027]:
        player_link = 'Cody Scates'
    elif stats[0].text == 'C. Warley' and id_num == [250812004, 250819028, 
                                                     250826021, 250902004]:
        player_link = 'Carter Warley'
    elif stats[0].text == 'B. Kennedy' and id_num in [250812020,250902002]:
        player_link = 'Brandon Kennedy'
    elif stats[0].text == 'S. Breeden' and id_num == 250901010:
        player_link = 'Sam Breeden'
    elif stats[0].text == 'L. Smith' and id_num == 250901003:
        player_link = 'Leroy Smith'
    elif stats[0].text == 'J. Jacobs' and id_num in [250818017, 250901017]:
        player_link = 'Joel Jacobs'
    elif stats[0].text == 'C. Kelley' and id_num == 250901033:
        player_link = 'Chris Kelley'
    elif stats[0].text == 'H. Lira' and id_num == 250901029:
        player_link = 'Hugo Lira'
    elif stats[0].text == 'C. Snyder' and id_num in [250820034, 250901027]:
        player_link = 'Chris Snyder'
    elif stats[0].text == 'D. Davis' and id_num in [280824011, 280828011]:
        player_link = 'D. Davis'
    elif stats[0].text == 'R. Hunt' and id_num == 280807022:
        invalid = True
    elif stats[0].text == 'T. Jones' and id_num == 260819028:
        invalid = True
    elif stats[0].text == 'D. Reid' and id_num == 250811009:
        invalid = True
    elif stats[0].text == 'B. Purify':
        invalid = True
    elif stats[0].text == 'M. Hayes' and id_num in [320818024, 320809024]:
        invalid = True
    elif stats[0].text == 'A. Mosley' and id_num in [320830025, 320826007]:
        player_link = 'http://espn.go.com/nfl/player/stats/_/id/' + \
                      '15254/anthony-mosley'
    elif stats[0].text == 'E. McGee' and id_num == 320825013:
        player_link = 'http://espn.go.com/nfl/player/_/id/14804/eddie-mcgee'
    elif stats[0].text == 'L. Johnson' and id_num in [321014027, 320916019, 
                                                      320817027, 320810015, 
                                                      320824027, 320829028,
                                                      321230001]:
        player_link = 'http://espn.go.com/nfl/player/_/id/15398/leonard-johnson'
    elif stats[0].text == 'M. Brown' and id_num in [320830030, 320810030]:
        player_link = 'Mike Brown'
    elif stats[0].text == 'J. Allen' and id_num in [320930012, 321007012]:
        player_link = 'http://espn.go.com/nfl/player/_/id/14990/jeff-allen'
    elif stats[0].text == 'M. Martin' and id_num in [321021002, 321011010, 
                                                     321007016, 320930034, 
                                                     320923010, 320916024, 
                                                     320909010, 320830010, 
                                                     320817027, 320811026]:
        player_link = 'http://espn.go.com/nfl/player/_/id/14988/mike-martin'
    else:
        print stats[0].text
        raise Exception('exception not found')
    return player_link, invalid

