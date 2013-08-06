import json
from itertools import groupby
from pyramid.view import view_config
from sqlalchemy import and_, or_
from sqlalchemy.orm import eagerload
from bizarro.models import DBSession
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.play_by_play import *

class GameView(object):
    def __init__(self, request):
        self.request = request
        self.sport = request.matchdict['sport']
        self.league = League.get(abbr=request.matchdict['league']).one()    
        self.game_id = request.matchdict['game_id'] 
        self.game = Game.get_game(game_id=self.game_id)
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'game': self.game
        }
    
    @view_config(route_name='game', 
                 renderer='bizarro.templates:games/football_boxscore.jinja2',
                 match_param='sport=football')
    @view_config(route_name='game_boxscore', 
                 renderer='bizarro.templates:games/football_boxscore.jinja2',
                 match_param='sport=football')
    def football_boxscore(self):
        page = 'boxscore'
        team_stats = FootballTeamStat.get(game=self.game).all()
        stats = PlayerStat.get_game(game=self.game)
        stats = PlayerStat.sorted_game_stats(stats=stats)      
        headers = FootballTeamStat.headers()
        models = PlayerStat.full_map()
        self.data.update({
            'page': page,
            'team_stats': team_stats,
            'stats': stats,
            'headers': headers,
            'models': models
        })
        return self.data
    
    @view_config(route_name='game', 
                 renderer='bizarro.templates:games/basketball_boxscore.jinja2',
                 match_param='sport=basketball')
    @view_config(route_name='game_boxscore', 
                 renderer='bizarro.templates:games/basketball_boxscore.jinja2',
                 match_param='sport=basketball')
    def basketball_boxscore(self):
        page = 'boxscore'
        team_stats = BasketballTeamStat.get(game=self.game).all()
        players = GamePlayer.get_game(game=self.game)
        players = Game.sorted_stats(players=players)
        stats = PlayerStat.get_game(game=self.game)
        stats = {stat.player:stat for stat in stats}
        self.data.update({
            'page': page,
            'team_stats': team_stats,
            'stats': stats,
            'players': players
        })
        return self.data
    
    @view_config(route_name='game_plays', 
                 renderer='bizarro.templates:games/plays.jinja2')
    def plays(self):    
        sport = request.matchdict['sport']
        league = request.matchdict['league']    
        game_id = request.matchdict['game_id']
        session = create_session(True)
        game = session.query(Game)\
                      .filter(Game.id==game_id)\
                      .one()
        plays = session.query(Play)\
                       .with_polymorphic('*')\
                       .filter(Play.game_id==game_id)\
                       .all()
        possessions = []
        possession = []
        for play in plays:
            event_type = play.event_type
            possession.append(play)
            if event_type in ['shot', 'steal', 'foul', 'violation']:
                possessions.append(possession)
                possession = []
        '''
        original_starters = starters[:]
        for play in plays:
            if play.event_type == 'substitution':
                if play.period == 3:
                    starters = original_starters
                print 'out',play.player_out
                print 'in', play.player_in
                starters.remove(play.player_out)
                starters.append(play.player_in)
                print starters
        '''
        data = {
            'sport': sport,
            'league': league,
            'game': game,
            'plays': plays,
            'possessions': possessions,
        }
        return data
    
    @view_config(route_name='game_shots', 
                 renderer='bizarro.templates:games/shots.jinja2')
    def shots(self):
        session = DBSession()
        shot_cords = session.query(ShotCoordinates)\
                       .join(Shot)\
                       .options(eagerload('shot.shooter'),
                                eagerload('shot.team'))\
                       .filter(Shot.game_id==self.game.id)\
                       .order_by(Shot.period)\
                       .all()
        json_shots = []
        shooters = []
        for shot_cord in shot_cords:
            shot = shot_cord.shot
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
                        'shooter_name': shot.shooter.person.names[0].full_name,
                        'shooter_id': shot.shooter_id,
                        'team_name': shot.team.name,
                        'team_id': shot.team_id,
                        }
            shooters.append({'shooter_name': shot_info['shooter_name'], 
                            'shooter_id': shot_info['shooter_id']})
            json_shots.append(shot_info)
        json_shots = json.dumps(json_shots)
        self.data.update({
            'shot_cords': shot_cords,
            'json_shots': json_shots,
            'shooters': shooters
        })
        return data
    


