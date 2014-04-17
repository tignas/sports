import re
import json
import datetime
import urllib, urllib2
from pprint import pprint
from BeautifulSoup import BeautifulSoup
from sqlalchemy import desc
from connect_db import *
from bizarro.models.teams import *
from bizarro.models.stats import *
from nfl.games import game_ids as nfl_game_ids
from nfl.games import nfl_boxscore

session = create_session(True)

def boxscore_game_id(game_id):
    game_external_id = session.query(GameExternalID)\
                               .join(Game)\
                               .filter(Game.id==game_id)\
                               .one()
    nba_boxscore(game_external_id.external_id)

def game_ids(league_abbr):
    league = session.query(League).filter(League.abbr==league_abbr).one()
    if league.abbr == 'nfl':
        return nfl_game_ids(league)
    elif league.abbr == 'nba':
        source_name = 'espn'
        end_date = datetime.date(year=2013, month=4, day=01)
        day = datetime.timedelta(days=1)
        start_date = datetime.datetime.now().date()
        date = start_date
        while date > end_date:
            date -= day
            date_string = date.strftime('%Y%m%d')
            print date_string
            score_url = 'http://scores.espn.go.com/nba/scoreboard?date=%s' 
            score_url %= date_string
            result = urllib2.urlopen(score_url)
            body = BeautifulSoup(result)
            game_search = r'\b-gamebox\b'
            games = body.findAll("div", attrs={"id":re.compile(game_search)})
            external_ids = [game['id'].partition('-')[0] for game in games]
            for external_id in external_ids:            
                game_external_id, created = get_or_create(session, 
                                                      GameExternalID,
                                                      external_id=external_id,
                                                      league_id=league.id,
                                                      source_name=source_name,
                                                      boxscore=False)

def import_boxscores(league):
    session = create_session(True)
    league = session.query(League).filter_by(abbr=league).one()
    if league.abbr == 'nba':
        bad_game_ids = [
            '400400517', '400400488', '400400474', '400400472', '400400471', 
            '400400466', '400400464', '400400463', '400400462', '400400461', 
            '310111001', '301102018', '301022014', '301016024', '301016005', 
            '301014029', '301014025', '301012014', '301007138', '301003143', 
            '301003017', '300206027', '291020012', '291004016', '291003007', 
            '290211026', '281021009', '281019138', '281018013', '281014028', 
            '281010019', '271019027', '271019002', '271018136', '271017028', 
            '271015009', '271013024', '271011132', '271011131', '271011018', 
            '271011013', '271011010', '271009130', '271009013', '271007129', 
            '271006128', '261219021', '261219004', '261214003', '261010020', 
            '251129026', '251129024', '251129023', '251129020', '251129016', 
            '251129015', '251129010', '251128009', '251107030', '251104024', 
            '251104020', '251104019', '251104018', '251104012', '251104009', 
            '251104007', '251104002', '251028018', '251018023', '251018022', 
            '251018018', '251018014', '251018013', '251018011', '251018008', 
            '251018003', '251017030', '251017026', '251017026', '251017010', 
            '251017004', '251016023', '251016018', '251016008', '251015029', 
            '251015024', '251015021', '251015017', '251015015', '251015014', 
            '251015007', '251011013', '241015014', '231005006', '400277733', 
            '400278133', '291018018', '291012005', '291009024', '291008132',
            '291006021', '400278934',
        ]
        all_star_games = [
            '320226031', '310220032', '300214032', '290215032', '280217032', 
            '270218032', '260219032', '250220032', '240215032', '230209031', 
            '220210031', '400436572'
        ]
    elif league.abbr == 'nfl':
        bad_game_ids = ['280815010']
        all_star_games = []
    external_game_ids = session.query(GameExternalID)\
                               .filter(GameExternalID.boxscore==None,
                                       GameExternalID.league_id==league.id)\
                               .filter(not_(GameExternalID.external_id\
                                                          .in_(bad_game_ids)))\
                               .filter(not_(GameExternalID.external_id\
                                                         .in_(all_star_games)))\
                               .order_by(desc(GameExternalID.external_id))\
                               .all()
    for external_game_id in external_game_ids:
        external_id = external_game_id.external_id
        print external_id
        if league.abbr == 'nba':
            game = nba_boxscore(external_id)
        elif league.abbr == 'nfl':
            game = nfl_boxscore(external_id)
        external_game_id.game_id = game.id
        external_game_id.boxscore = True
        save(session, external_game_id)        

def assign_game_type(league):
    """For all games assign pre, reg, or post game types."""
    league = session.query(League).filter_by(abbr=league).one()
    seasons = session.query(Season)\
                     .filter(Season.league_id==league.id,
                             Season.year>2004)\
                     .order_by('year')
    day = datetime.timedelta(days=1)
    for season in seasons:
        print season.year
        preseason_games = session.query(Game)\
                .filter(Game.game_time.between(season.preseason_start, 
                                               season.preseason_end+day),
                        Game.league_id==league.id)\
                .update({'game_type': 'pre', 'season_id': season.id}, 
                         synchronize_session=False)
        session.commit()
        regular_games = session.query(Game)\
                .filter(Game.game_time.between(season.regular_start, 
                                               season.regular_end+day),
                        Game.league_id==league.id)\
                .update({'game_type': 'reg', 'season_id': season.id}, 
                         synchronize_session=False)
        session.commit()
        if season.postseason_start:
            postseason_games = session.query(Game)\
                    .filter(Game.game_time.between(season.postseason_start, 
                                                   season.postseason_end+day),
                            Game.league_id==league.id)\
                    .update({'game_type': 'post', 'season_id': season.id}, 
                             synchronize_session=False)
        session.commit()

def assign_game_weeks():
    """For all seasons assign the game week for each game."""
    league = session.query(League).filter_by(abbr='nfl').one()
    seasons = session.query(Season).filter_by(league_id=league.id)
    day = datetime.timedelta(days=1)
    for season in seasons:
        start_date = season.regular_start
        for week in range(1, 18):
            games = session.query(Game)\
                           .filter(Game.game_time.between(start_date, 
                                                          start_date+day*7))
            for game in games:
                football_game, created = get_or_create(session, FootballGame, 
                                                    game_id=game.id, week=week)
            start_date += day*7
            
def flatten_stats(league):
    players = session.query(GamePlayer)\
                     .join(Game)\
                     .filter(Game.league_id==1)\
                     .order_by(GamePlayer.id)\
                     .count()
    for num, gp in enumerate(players):
        print num
        stats = session.query(PlayerStat)\
                       .with_polymorphic('*')\
                       .filter_by(game_id=gp.game_id, team_id=gp.team_id, 
                                  player_id=gp.player_id)
        offensive_stat = {
            'player_id': gp.player_id,
            'team_id': gp.team_id,
            'game_id': gp.game_id
        }
        is_ = False
        for stat in stats:
            stat_type = stat.stat_type
            if stat_type in ['passing', 'rushing', 'receiving', 'fumble', 
                             'return']:
                is_ = True
                stat = stat.as_dict()
                del stat['id']
                prefix = stat_type + '_'
                if stat_type == 'return':
                    prefix = stat.pop('return_type') + '_' + prefix
                for key, v in stat.items():
                    offensive_stat[prefix + key] = v
        session.add(FootballOffensiveStat(**offensive_stat))
    session.commit()
    
def assign_defensive_stats():
    games = session.query(Game)\
                   .join(Season)\
                   .filter(Game.league_id==1, Game.game_type=='reg',
                           Season.year.in_(range(2005, 2013)))\
                   .all()
    for num, game in enumerate(games):
        team = game.home_team
        stats = game.team_stats
        if game.home_team == stats[0].team:
            home_stats, away_stats = stats
        else:
            away_stats, home_stats = stats
        if not game.home_team == home_stats.team:
            raise Exception('team mismatch')
        home_stat = FootballDefenseSpecialTeamsStat()
        away_stat = FootballDefenseSpecialTeamsStat()
        #yards allowed
        home_stat.yards_allowed = away_stats.yards 
        away_stat.yards_allowed = home_stats.yards
        #Sacks
        home_stat.sack_total = home_stats.sack_total
        away_stat.sack_total = away_stats.sack_total
        home_stat.sack_yards = home_stats.sack_yards
        away_stat.sack_total = away_stats.sack_total
        #Fumbles
        home_stat.fumbles_recovered = away_stats.fumbles_lost
        away_stat.fumbles_recovered = home_stats.fumbles_lost
        #Interceptions
        home_stat.interceptions = away_stats.interceptions
        away_stat.interceptions = home_stats.interceptions
        #touchdowns
        if home_stats.defensive_special_teams_tds:
            home_stat.touchdowns = home_stats.defensive_special_teams_tds
            away_stat.touchdowns = away_stats.defensive_special_teams_tds
        else:
            home_stat.touchdowns = 0
            away_stat.touchdowns = 0
        home_stat.points_allowed = game.away_score - away_stat.touchdowns * 7
        away_stat.points_allowed = game.home_score - home_stat.touchdowns * 7
        session.add(home_stat)
        session.add(away_stat)
    session.commit()
    
