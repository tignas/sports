import json
import numpy
from itertools import groupby
from pyramid.view import view_config
from sqlalchemy.orm import aliased, eagerload
from sqlalchemy import and_, or_, desc, func
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.play_by_play import *

class TeamView(object):
    
    def __init__(self, request):
        page = request.matched_route.name.split('_')[1]
        self.request = request
        self.sport = request.matchdict['sport']
        self.league = League.get(abbr=request.matchdict['league']).one()
        self.t_query = Team.get_team(league=self.league,
                                     team_abbr=request.matchdict['team_abbr'])
        self.team = self.t_query.one()
        self.team_links = Team.full_links()
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'team_links': self.team_links,
            'team': self.team,
            'page': page
        }

    @view_config(route_name='team_home', 
                 renderer='bizarro.templates:teams/team.jinja2')
    def team_home(self):
        return self.data
    
    @view_config(route_name='team_roster',
                 renderer='bizarro.templates:teams/roster.jinja2')
    def roster(self):
        team = Team.get_roster(t_query=self.t_query).one()
        self.data.update({
            'team': team,
        })
        return self.data

    @view_config(route_name='team_schedule',
                 renderer='bizarro.templates:teams/schedule.jinja2')
    def schedule(self):
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2012))
        games = Game.team_schedule(team=self.team,
                                   game_type=game_type, 
                                   year=season_year)
        self.data.update({
            'game_type': game_type,
            'season_year': season_year,
            'games': games,
        })
        return self.data
    
    @view_config(route_name='team_stats', 
                 renderer='bizarro.templates:teams/football_stats.jinja2',
                 match_param='sport=football')
    def football_stats(self):        
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2012))
        models, stats = Player.team_stats(team=self.team, 
                                          game_type=game_type, 
                                          season_year=season_year)
        self.data.update({
            'game_type': game_type,
            'season_year': season_year,
            'stats': stats,
            'models': models
        })
        return self.data
    
    @view_config(route_name='team_stats', 
                 renderer='bizarro.templates:teams/stats.jinja2',
                 match_param='sport=basketball')
    def basketball_stats(self):
        self.team = Team.get_roster(t_query=self.t_query).one()
        stats = {}  
        Stat = aliased(BasketballBoxScoreStat)
        for player in players:
            stat = session.query(func.sum(Stat.minutes).label('minutes'),
                                 func.sum(Stat.field_goals_made)
                                     .label('field_goals_made'),
                                 func.sum(Stat.field_goals_attempted)
                                     .label('field_goals_attempted'),
                                 func.sum(Stat.threes_made).label('threes_made'),
                                 func.sum(Stat.threes_attempted)
                                     .label('threes_attempted'),
                                 func.sum(Stat.free_throws_made)  
                                     .label('free_throws_made'),
                                 func.sum(Stat.free_throws_attempted)
                                     .label('free_throws_attempted'),
                                 func.sum(Stat.offensive_rebounds)
                                     .label('offensive_rebounds'),
                                 func.sum(Stat.defensive_rebounds)
                                     .label('defensive_rebounds'),
                                 func.sum(Stat.rebounds).label('rebounds'),
                                 func.sum(Stat.assists).label('assists'),
                                 func.sum(Stat.steals).label('steals'),
                                 func.sum(Stat.blocks).label('blocks'),
                                 func.sum(Stat.turnovers).label('turnovers'),
                                 func.sum(Stat.personal_fouls)
                                     .label('personal_fouls'),
                                 func.sum(Stat.plus_minus).label('plus_minus'),
                                 func.sum(Stat.points).label('points'))\
                          .filter(Stat.team==self.team, 
                                  Stat.player==player)\
                          .one()
            stats[player] = stat
        game_types = {
        'pre': 'preseason',
        'reg': 'regular',
        'post': 'postseason',
        }
        seasons = range(2004, 2013)
        self.data.update({
            'stats': stats,
            'game_types': game_types,
            'seasons': seasons,
            'page': page
        })  
        return self.data
    
    @view_config(route_name='team_shots', 
                 renderer='bizarro.templates:teams/shots.jinja2')
    def shots(self):
        session = DBSession()
        page = 'shots'
        team = self.team
        shot_cords = session.query(ShotCoordinates)\
                            .join(Shot)\
                            .options(eagerload('shot.team'),
                                     eagerload('shot.game'),
                                     eagerload('shot.game.home_team'),
                                     eagerload('shot.game.away_team'),
                                     eagerload('shot.shooter'))\
                            .filter(Shot.team==team)\
                            .all()
        json_shots = []
        for shot_cord in shot_cords:
            shot = shot_cord.shot
            game = shot.game
            if game.away_team == team:
                opponent = game.home_team
            elif game.home_team == team:
                opponent = game.away_team
            else:
                print 'home', game.home_team
                print 'away', game.away_team
                print 'player team', team
                raise Exception("team doesn't exist")
            shot_info = {'shot_id': shot.id,
                        'shooter_name': shot.shooter.person.names[0].full_name,
                        'shooter_id': shot.shooter_id,
                        'period': shot.period,
                        'time_of_game': shot.time_of_game.strftime('%H:%M'),
                        'home_score': shot.home_score,
                        'away_score': shot.away_score,
                        'x': shot_cord.x,
                        'y': shot_cord.y,
                        'length': shot_cord.length,
                        'make': shot.make,
                        'shot_type': shot.shot_type,
                        'game_id': game.id,
                        'opponent_name': opponent.name,
                        'opponent_id': opponent.id,
                        }
            json_shots.append(shot_info)
        json_shots = json.dumps(json_shots)
        self.data.update({
            'json_shots': json_shots
        })
        return self.data
