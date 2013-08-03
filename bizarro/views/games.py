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
        self.league = request.matchdict['league']    
        self.game_id = request.matchdict['game_id']        
        session = DBSession()
        self.game = session.query(Game)\
                      .options(eagerload('away_team'),
                               eagerload('home_team'),
                               eagerload('home_scores'),
                               eagerload('away_scores'))\
                      .get(self.game_id)
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'game': self.game
        }
        
    @view_config(route_name='game', 
                 renderer='bizarro.templates:games/boxscore.jinja2')
    @view_config(route_name='game_boxscore', 
                 renderer='bizarro.templates:games/boxscore.jinja2')
    def boxscore(self):
        session = DBSession()
        sport = self.sport
        game = self.game
        if sport == 'football':
            team_stats = session.query(FootballTeamStat)\
                                .filter(FootballTeamStat.game==game)
            stats = session.query(PlayerStat)\
                           .options(eagerload('player'),
                                    eagerload('team'))\
                           .with_polymorphic('*')\
                           .filter(PlayerStat.game_id==game.id)\
                           .all()
            key = lambda x: x.team
            stats = groupby(sorted(list(stats), key=key), key=key)
            stats = {team:list(stats) for team, stats in stats}
            game_stats = {}
            for team, stat_list in stats.iteritems():
                game_stats[team] = {}
                key = lambda x: x.stat_type
                stat_list = sorted(stat_list, key=key)
                for stat_type, these_stats in groupby(stat_list, key=key):
                    if stat_type == 'return':
                        game_stats[team]['kick_return'] = []
                        game_stats[team]['punt_return'] = []
                        for stat in list(these_stats):
                            return_type = '%s_return' % stat.return_type
                            game_stats[team][return_type].append(stat)
                    else:
                        game_stats[team][stat_type] = list(these_stats)
            stat_players = game_stats
        elif sport == 'basketball':
            team_stats = session.query(BasketballTeamStat)\
                                .filter(BasketballTeamStat.game_id==game.id)\
                                .all()
            stats = session.query(GamePlayer, BasketballBoxScoreStat)\
                           .options(eagerload('player'),
                                    eagerload('player.positions'),
                                    eagerload('team'),
                                    eagerload('team.league'))\
                           .join(BasketballBoxScoreStat, 
                                       and_(BasketballBoxScoreStat.game_id==GamePlayer.game_id,
                                            BasketballBoxScoreStat.player_id==GamePlayer.player_id))\
                           .filter(GamePlayer.game==game)\
                           .all()
            dnps = session.query(GamePlayer)\
                           .options(eagerload('player'),
                                    eagerload('player.positions'),
                                    eagerload('team'),
                                    eagerload('team.league'))\
                          .join(GamePlayerDNP)\
                          .filter(GamePlayer.game==game)\
                          .all()
            key = lambda x: x[0].team
            stats = groupby(sorted(list(stats), key=key), key=key)
            stats = {team:list(stats) for team, stats in stats}
            key = lambda x: x.team
            dnps = groupby(sorted(list(dnps), key=key), key=key)
            dnps = {team:list(players) for team, players in dnps}
            stat_players = {}
            for team, players in stats.iteritems():
                bench = []
                starters = []
                for player, stat in players:
                    if player.starter:
                        starters.append(stat)
                    else:
                        bench.append(stat)
                stat_players[team] = {}
                stat_players[team]['bench'] = bench
                stat_players[team]['starter'] = starters
            for team, players in dnps.iteritems():
                stat_players[team]['dnp'] = players
        officials = session.query(Person)\
                           .join(Official, GameOfficial)\
                           .filter(GameOfficial.game_id==game.id)
        self.data.update({
            'team_stats': team_stats,
            'stats': stat_players,
            'officials': officials
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
    


