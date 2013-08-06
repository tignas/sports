import json
from itertools import groupby
from pyramid.view import view_config
from sqlalchemy import func
from sqlalchemy.orm import eagerload
from bizarro.models import DBSession
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.play_by_play import *
from bizarro.models.fantasy import FootballOffenseProjection, FootballKickingProjection
from bizarro.api.sums import sum_request
    
class PlayerView(object):
    
    def __init__(self, request):
        self.request = request
        page = request.matched_route.name.split('_')[-1]
        self.sport = request.matchdict['sport']
        self.league = League.get(abbr=request.matchdict['league']).one()
        self.player_id = request.matchdict['player_id']
        self.player = DBSession.query(Player).get(self.player_id)
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'player': self.player,
            'player_links': Player.links(),
            'page': page
        }
        
    @view_config(route_name='player', 
                 renderer='bizarro.templates:players/player.jinja2')
    def player_home(self):
        return self.data
    
    @view_config(route_name='player_stat',
                 renderer='bizarro.templates:players/stats.jinja2',
                 match_param='sport=football')
    def football_stat(self):
        game_type = self.request.GET.get('game_type', 'reg')
        info = {
            'sport': self.sport,
            'league': self.league,
            'game_type': game_type,
            'player': self.player
        }
        game_stats = PlayerStat.player_stats(**info)
        stats = Player.stats_by_season(game_stats)
        self.data.update({
            'stats': stats,
            'game_type': game_type,
        })
        return self.data
    
    @view_config(route_name='player_projections',
                 renderer='bizarro.templates:players/projections.jinja2')
    def projections(self):
        season = self.request.GET.get('season', 2013)
        if 'pk' in self.player.position_string():
            model = FootballKickingProjection
        else:
            model = FootballOffenseProjection
        projs = model.projections(player=self.player, season=season).all()
        averages = model.average(projs)
        abbrs = model.abbr()
        headers = model.grouped_headers()
        if self.request.user:
            print self.request.user
        self.data.update({
            'projs': projs,
            'averages': averages,
            'abbrs': abbrs,
            'headers': headers,
        })
        return self.data
                        
    
    @view_config(route_name='player_shots', 
                 renderer='bizarro.templates:players/shots.jinja2')
    def shots(self):
        team = self.player.teams[0]
        shot_cords = DBSession.query(ShotCoordinates)\
                            .options(eagerload('shot.team'),
                                     eagerload('shot.game'),
                                     eagerload('shot.game.home_team'),
                                     eagerload('shot.game.away_team'))\
                            .join(Shot)\
                            .filter(Shot.shooter_id==self.player.id)\
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
                        'points': shot.points,
                        'opponent_name': opponent.name,
                        'opponent_id': opponent.id,
                        }
            json_shots.append(shot_info)
        json_shots = json.dumps(json_shots)
        self.data.update({'shot_cords': shot_cords,
                     'json_shots': json_shots})
        return data
    
    
    
    
    
    
    
