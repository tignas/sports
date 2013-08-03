from sqlalchemy import func
from sqlalchemy.orm import aliased
from bizarro.models.stats import *
from bizarro.models.fantasy import *

def sum_request(model):
    Stat = aliased(model)
    if model == FootballPassingStat:
        sum_query = [
            func.sum(Stat.attempts).label('passing_attempts'),
            func.sum(Stat.completions).label('passing_completions'),
            func.sum(Stat.yards).label('passing_yards'),
            func.sum(Stat.touchdowns).label('passing_touchdowns'),
            func.sum(Stat.interceptions).label('passing_interceptions'),
            func.sum(Stat.sacks).label('passing_sacks'),
            func.sum(Stat.sack_yards).label('passing_sack_yards')
        ]
    elif model == FootballReceivingStat:
        sum_query = [
            func.sum(Stat.receptions).label('receiving_receptions'),
            func.sum(Stat.targets).label('receiving_targets'),
            func.sum(Stat.yards).label('receiving_yards'),
            func.sum(Stat.touchdowns).label('receiving_touchdowns'),
            func.max(Stat.longest).label('receiving_longest')
        ]
    elif model == FootballRushingStat:
        sum_query = [
            func.sum(Stat.attempts).label('rushing_attempts'),
            func.sum(Stat.yards).label('rushing_yards'),
            func.sum(Stat.touchdowns).label('rushing_touchdowns'),
            func.max(Stat.longest).label('rushing_longest')
        ]
    elif model == FootballFumbleStat:
        sum_query = [
            func.sum(Stat.fumbles).label('fumbles_total'),
            func.sum(Stat.recovered).label('fumbles_recovered'),
            func.sum(Stat.lost).label('fumbles_lost')
        ]
    elif model == FootballDefensiveStat:
        sum_query = [
            func.sum(Stat.tackles).label('defensive_tackles'),
            func.sum(Stat.solo).label('defensive_solo'),
            func.sum(Stat.sacks).label('defensive_sacks'),
            func.sum(Stat.tackles_for_loss).label('defensive_tackles_for_loss'),
            func.sum(Stat.pass_deflections).label('defensive_pass_deflectiosn'),
            func.sum(Stat.qb_hits).label('defensive_qb_hits'),
            func.sum(Stat.touchdowns).label('defensive_touchdowns')
        ]
    elif model == FootballReturnStat:
        sum_query = [
            func.sum(Stat.total).label('return_total'),
            func.sum(Stat.yards).label('return_yards'),
            func.sum(Stat.touchdowns).label('return_touchdowns'),
            func.max(Stat.longest).label('return_longest')
        ]
    elif model == FootballKickingStat:
        sum_query = [
            func.sum(Stat.fg_made).label('fg_made'),
            func.sum(Stat.fg_attempts).label('fg_attempts'),
            func.sum(Stat.xp_made).label('xp_made'),
            func.sum(Stat.xp_attempts).label('xp_attempts'),
            func.max(Stat.longest).label('longest')
        ]
    elif model == FootballPuntingStat:
        sum_query = [
            func.sum(Stat.total).label('punting_total'),
            func.sum(Stat.yards).label('punting_yards'),
            func.sum(Stat.touchbacks).label('punting_touchbacks'),
            func.sum(Stat.inside_20).label('punting_inside_20'),
            func.max(Stat.longest).label('punting_longest')
        ]
    elif model == FootballInterceptionStat:
        sum_query = [
            func.sum(Stat.total).label('interception_tototal'),
            func.sum(Stat.yards).label('interception_yards'),
            func.sum(Stat.touchdowns).label('interception_touchdowns')
        ]
    elif model == FootballOffensiveStat:
        sum_query = [
        func.sum(Stat.passing_completions).label('passing_completions'),
        func.sum(Stat.passing_attempts).label('passing_attempts'),
        func.sum(Stat.passing_yards).label('passing_yards'),
        func.sum(Stat.passing_sacks).label('passing_sacks'),
        func.sum(Stat.passing_sack_yards).label('passing_sack_yards'),
        func.sum(Stat.passing_interceptions).label('passing_interceptions'),
        func.sum(Stat.passing_touchdowns).label('passing_touchdowns'),
        func.sum(Stat.rushing_attempts).label('rushing_attempts'),
        func.sum(Stat.rushing_yards).label('rushing_yards'),
        func.sum(Stat.rushing_touchdowns).label('rushing_touchdowns'),
        func.sum(Stat.receiving_receptions).label('receiving_receptions'),
        func.sum(Stat.receiving_targets).label('receiving_targets'),
        func.sum(Stat.receiving_yards).label('receiving_yards'),
        func.sum(Stat.receiving_touchdowns).label('receiving_touchdowns'),
        func.sum(Stat.kick_return_yards + Stat.punt_return_yards).label('return_yards'),
        func.sum(Stat.kick_return_touchdowns + Stat.punt_return_touchdowns).label('return_touchdowns'),
        func.sum(Stat.fumble_lost + Stat.fumble_recovered).label('fumbles_total'),
        func.sum(Stat.fumble_lost).label('fumbles_lost'),
        func.sum(Stat.fumble_recovered).label('fumbles_recovered'),
        ]
    elif model == BasketballBoxScoreStat:
        sum_query = [
            func.count(Stat.game_id).label('gp'),
            func.sum(Stat.minutes).label('min'),
            func.sum(Stat.field_goals_made).label('fgm'),
            func.sum(Stat.field_goals_attempted).label('fga'),
            func.sum(Stat.threes_made).label('3ptm'),
            func.sum(Stat.threes_attempted).label('3pta'),
            func.sum(Stat.free_throws_made).label('ftm'),
            func.sum(Stat.free_throws_attempted).label('fta'),
            func.sum(Stat.offensive_rebounds).label('oreb'),
            func.sum(Stat.defensive_rebounds).label('dreb'),
            func.sum(Stat.rebounds).label('reb'),
            func.sum(Stat.assists).label('ast'),
            func.sum(Stat.steals).label('stl'),
            func.sum(Stat.blocks).label('blk'),
            func.sum(Stat.turnovers).label('tos'),
            func.sum(Stat.personal_fouls).label('pf'),
            func.sum(Stat.plus_minus).label('+/-'),
            func.sum(Stat.points).label('pts')
        ]
    elif model == FootballTeamStat:
        sum_query = [
            func.count(Stat.sack_total).label('sacks'),
            func.count(Stat.defensive_special_teams_tds).label('td'),
            func.count(Stat.interceptions).label('interceptions'),
        ]
    elif model == GamePlayer:
        sum_query = [
            func.count(Stat.game_id).label('gp')
        ]
    return Stat, sum_query
    
def average_request(model):
    Stat = aliased(model)
    if model == FootballOffenseProjection:
        avg_query = [
            func.avg(Stat.passing_attempts).label('passing_attempts'),
            func.avg(Stat.passing_completions).label('passing_completions'),
            func.avg(Stat.passing_yards).label('passing_yards'),
            func.avg(Stat.passing_touchdowns).label('passing_touchdowns'),
            func.avg(Stat.passing_interceptions).label('passing_interceptions'),
            func.avg(Stat.passing_sacks).label('passing_sacks'),
            func.avg(Stat.rushing_attempts).label('rushing_attempts'),
            func.avg(Stat.rushing_yards).label('rushing_yards'),
            func.avg(Stat.rushing_touchdowns).label('rushing_touchdowns'),
            func.avg(Stat.receiving_yards).label('receiving_yards'),
            func.avg(Stat.receiving_touchdowns).label('receiving_touchdowns'),
            func.avg(Stat.receiving_receptions).label('receiving_receptions'),
            func.avg(Stat.receiving_targets).label('receiving_targets'),
            func.avg(Stat.fumbles_total).label('fumbles_total'),
            func.avg(Stat.fumbles_lost).label('fumbles_lost'),
            func.avg(Stat.two_pt).label('two_pt'),
            func.avg(Stat.return_yards).label('return_yards'),
            func.avg(Stat.return_touchdowns).label('return_touchdowns'),
        ]
    elif model == FootballKickingProjection:
        avg_query = [
            func.avg(Stat.u_40_miss).label('u_40_miss'),
            func.avg(Stat.u_40_make).label('u_40_make'),
            func.avg(Stat.o_50_miss).label('o_50_miss'),
            func.avg(Stat.o_50_make).label('o_50_make'),
            func.avg(Stat.b_40_50_miss).label('b_40_50_miss'),
            func.avg(Stat.b_40_50_make).label('b_40_50_make'),
            func.avg(Stat.xp_miss).label('xp_miss'),
            func.avg(Stat.xp_make).label('xp_make'),
        ]
    elif model == TeamDefenseProjection:
        avg_query = [
            func.avg(Stat.sacks).label('sacks'),
            func.avg(Stat.safeties).label('safeties'),
            func.avg(Stat.interceptions).label('interceptions'),
            func.avg(Stat.fumbles_forced).label('fumbles_forced'),
            func.avg(Stat.fumbles_recovered).label('fumbles_recovered'),
            func.avg(Stat.touchdowns).label('touchdowns'),
            func.avg(Stat.points_against).label('points_against'),
            func.avg(Stat.fantasy_points).label('fantasy_points'),
        ]
    return Stat, avg_query

def model_map(sport):
    if sport == 'football':
        map_ = {
            'passing': {
                'models': [FootballPassingStat, FootballRushingStat, 
                           FootballFumbleStat], 
                'positions': ['qb']
                }, 
            'receiving': {
                'models': [FootballReceivingStat, FootballRushingStat,
                           FootballFumbleStat],
                'positions': ['wr', 'te']
                }, 
            'rushing': {
                'models': [FootballRushingStat, FootballReceivingStat, 
                           FootballFumbleStat],
                'positions': ['hb', 'fb', 'rb']
                },
            'defensive': {
                'models': [FootballDefensiveStat, FootballInterceptionStat],
                'positions': ['cb', 's', 'fs', 'ss', 'de', 'lb', 'rolb', 
                              'lolb', 'mlb', 'db', 'dl', 'nt', 'le', 're',
                              'dt', 'ls']
                },
            'kicking': {
                'models': [FootballKickingStat],
                'positions': ['k', 'pk'],
            },
            'punting': {
                'models': [FootballPuntingStat],
                'positions': ['p'],
            },
            'return': {
                'models': [FootballReturnStat],
                'positions': ['qb', 'wr', 'te', 'hb', 'r', 'kr', 'rb', 'cb',
                              's', 'ath', 'fs', 'ss', 'de', 'lb', 'rolb', 
                              'lolb', 'mlb', 'db', 'dl', 'nt', 'le', 're',
                              'dt', 'ls']
            },
            'fantasy': {
                'offense': {
                    'models': [
                        GamePlayer,
                        FootballOffensiveStat,
                    ],
                    'positions': ['qb', 'rb', 'te', 'wr']
                },
                'kicking': {
                    'models': [GamePlayer, FootballKickingStat],
                    'positions': ['pk', 'k']
                },
                'defense': {
                    'models': [FootballTeamStat]
                }
            },
        }
    return map_
        
def position_map():
    map_ = {
        'qb': 'passing',
        'rb': 'rushing',
        'fb': 'rushing',
        'hb': 'rushing',
        'wr': 'receiving',
        'te': 'receiving',
        'k': 'kicking',
        'p': 'punting',
    }
    return map_
        
        
        
    
    
    
    
    
    
    
    
    
    
        
