import json
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
        self.request = request
        self.sport = request.matchdict['sport']
        league_abbr = request.matchdict['league']
        team_abbr = request.matchdict['team_abbr']
        session =  DBSession()
        self.team = session.query(Team)\
                           .join(LeagueTeam, League)\
                           .filter(League.abbr==league_abbr,
                                   Team.abbr==team_abbr)\
                           .one() 
        self.league = session.query(League)\
                             .filter(League.abbr==league_abbr)\
                             .one()
        self.team_links = Team.full_links()
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'team': self.team,
            'team_links': self.team_links,
        }

    @view_config(route_name='team_home', 
                 renderer='bizarro.templates:teams/team.jinja2')
    def team_home(self):
        page = 'home'
        self.data.update({
            'page': page
        })
        return self.data
    
    @view_config(route_name='team_roster',
                 renderer='bizarro.templates:teams/roster.jinja2')
    def roster(self):
        page = 'roster'
        session = DBSession()
        players = session.query(Player)\
                         .options(eagerload('positions'),
                                  eagerload('number'),
                                  eagerload('person.college'),
                                  eagerload('person.height_weight'),
                                  eagerload('league'))\
                         .join(TeamPlayer)\
                         .filter(TeamPlayer.team==self.team, 
                                 TeamPlayer.current==True)
        self.data.update({
            'players':players
        })
        return self.data

    @view_config(route_name='team_schedule',
                 renderer='bizarro.templates:teams/schedule.jinja2')
    @view_config(route_name='team_schedule',
                 xhr=True,
                 renderer='bizarro.templates:teams/schedule_table.jinja2')
    def schedule(self): 
        page = 'schedule'
        session =  DBSession()
        game_type = 'reg'
        season = 2012
        request = self.request
        if request.GET.has_key('game_type'):
            game_type = request.GET['game_type']
        if request.GET.has_key('season'):
            season = int(request.GET['season'])
        games = session.query(Game)\
                       .join(Season)\
                       .options(eagerload('away_team'),
                                eagerload('away_team.league'),
                                eagerload('league'),
                                eagerload('home_team'),
                                eagerload('home_team.league'))\
                       .filter(or_(Game.home_team==self.team, 
                                   Game.away_team==self.team),
                               Game.game_type==game_type,
                               Season.year==season)\
                       .order_by(Game.game_time)
        game_types = Game.game_types()
        self.data.update({
            'game_types': game_types,
            'games': games,
            'season': season,
            'game_type': game_type,
            'page': page
        })
        return self.data
    
    @view_config(route_name='team_stats', 
                 renderer='bizarro.templates:teams/stats.jinja2')
    def stats(self):
        session = DBSession()
        page = 'stats'
        players = session.query(Player)\
                         .options(eagerload('person'),
                                  eagerload('positions'),
                                  eagerload('league'))\
                         .join(TeamPlayer)\
                         .filter(TeamPlayer.team==self.team, 
                                 TeamPlayer.current==True)\
                         .all()
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
    
    @view_config(route_name='team_news', 
                 renderer='bizarro.templates:teams/news.jinja2')
    def news(self):
        session = DBSession()
        page = 'news'
        self.data.update({
            'page': page
        })
        return self.data
    
    @view_config(route_name='team_splits', 
                 renderer='bizarro.templates:teams/splits.jinja2')
    def splits(self):
        session = DBSession()
        page = 'splits'
        self.data.update({
            'page': page
        })
        return self.data

    @view_config(route_name='team_depth_chart', 
                 renderer='bizarro.templates:teams/depth_chart.jinja2')
    def depth_chart(self):
        session = DBSession()
        page = 'depth_chart'
        self.data.update({
            'page': page
        })
        return self.data

    @view_config(route_name='team_transactions', 
                 renderer='bizarro.templates:teams/transactions.jinja2')
    def transactions(self):
        session = DBSession()
        page = 'transactions'
        self.data.update({
            'page': page
        })
        return self.data
    
    @view_config(route_name='team_stadium', 
                 renderer='bizarro.templates:teams/stadium.jinja2')
    def stadium(self):
        session = DBSession()
        page = 'stadium'
        self.data.update({
            'page': page
        })
        return self.data
    
    @view_config(route_name='team_forum', 
                 renderer='bizarro.templates:teams/forum.jinja2')
    def forum(self):
            session = DBSession()
            page = 'forum'
            self.data.update({
                'page': page
            })
            return self.data
