import json
import datetime
from itertools import groupby
from pyramid.view import view_config
from pyramid.renderers import render_to_response
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import aliased, eagerload
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.media import *
from bizarro.models.play_by_play import *
    
@view_config(route_name='home',
             renderer='bizarro.templates:home.jinja2')
def home(request):
    page = 'bizarro home'
    league = DBSession.query(League).get(1)
    today = datetime.datetime.now().date()
    scores = Game.get_date(league=league, date=today)
    feed_sources = ['espn', 'si', 'cbs']
    data = {
        'page': page,
        'league': league,
        'scores': scores,
    }
    return data

class LeagueView(object):

    def __init__(self, request):
        self.request = request
        self.sport = request.matchdict['sport']
        league_abbr = request.matchdict['league']
        self.league = League.get(abbr=league_abbr).one()
        page = request.matched_route.name.split('_')[1]
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'page': page,
        }
    
    @view_config(route_name='league_home',
                 renderer='bizarro.templates:league/home.jinja2')
    def league_home(self):
        session = DBSession()
        tweets = []
        videos = Video.get(league=self.league, video_type='youtube').limit(10)
        articles = session.query(Article)\
                          .options(eagerload('source'))\
                          .order_by(desc(Article.updated))\
                          .limit(10)
        self.data.update({
            'articles': articles,
            'videos': videos,
            'tweets': tweets,
        })
        return self.data
    
    @view_config(route_name='league_teams',
                 renderer='bizarro.templates:league/teams.jinja2')
    def teams(self):
        conferences = Conference.get(league_id=self.league.id)
        self.data.update({
            'conferences': conferences,
            'team_links': Team.links(),
        })
        return self.data

    @view_config(route_name='league_scores', 
                 renderer='bizarro.templates:league/scores.jinja2')
    @view_config(route_name='league_scores',
                 xhr=True,
                 renderer='bizarro.templates:widgets/scores_full.jinja2')
    def scores(self):
        today = datetime.datetime.now().date()
        day = datetime.timedelta(days=1)
        yesterday = today-day
        if self.request.GET.has_key('date'):
            date = self.request.GET['date']
            date = datetime.datetime.strptime(date, '%m/%d/%Y').date()
        else:          
            date = yesterday
        games = Game.get_date(league=self.league, date=date)
        self.data.update({
            'games': games,
            'date': date,
            'game_links': Game.links()
        })
        return self.data
        
    @view_config(route_name='league_schedule', 
                 renderer='bizarro.templates:league/football/schedule.jinja2',
                 match_param="league=nfl")
    @view_config(route_name='league_schedule', 
                 renderer='bizarro.templates:league/basketball/schedule.jinja2',
                 match_param="league=nba")
    def schedule(self):
        season = int(self.request.GET.get('season', 2012))
        game_type = self.request.GET.get('game_type', 'reg')
        games = Game.get_season(league=self.league, game_type=game_type,    
                                year=season)
        if self.league.abbr == 'nfl':
            key = lambda x: x.week()
        elif self.league.abbr == 'nba':
            key = lambda x: x.game_time.date()
        games = groupby(sorted(list(games), key=key), key=key)
        self.data.update({
            'games': games,
            'season_year': season,
            'game_type': game_type
        })
        return self.data

    @view_config(route_name='league_players', 
                 renderer='bizarro.templates:league/players.jinja2')
    def players(self):
        players = Player.current_players(league=self.league)
        self.data.update({
            'players': players,
        })
        return self.data
        
class StandingsView(object):

    def __init__(self, request):
        self.request = request
        self.sport = request.matchdict['sport']
        league_abbr = request.matchdict['league']
        self.league = League.get(abbr=league_abbr).one()
        page = request.matched_route.name.split('_')[1]
        season = int(request.GET.get('season', 2012))
        game_type =request.GET.get('game_type', 'reg')
        teams = Team.season_wins(season=season, game_type=game_type, 
                                 league=self.league)
        self.teams = [{k:v if v else 0 for k, v in team._asdict().iteritems()} 
                        for team in teams]
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'season_year': season,
            'game_type': game_type,
            'page': page,
            'view_type': request.matchdict.get('view_type', 'division'),
            'view_types': ['league', 'conference', 'division']
        }
        
    @view_config(route_name='league_standings', 
                 renderer='bizarro.templates:league/standings/divisions.jinja2')
    @view_config(route_name='league_standings_view', 
                 renderer='bizarro.templates:league/standings/divisions.jinja2',
                 match_param='view_type=division')
    def standings(self):
        key = lambda x: x['Team'].division.conference
        team_dict = {}
        conference_teams = groupby(sorted(list(self.teams), key=key), key=key)
        for conference, teams in conference_teams:
            key = lambda x: x['Team'].division
            division_teams = groupby(sorted(list(teams), key=key), key=key)
            team_dict[conference] = {}
            for division, teams in division_teams:
                key = lambda x: x['home_wins'] + x['away_wins']
                teams = sorted(list(teams), key=key, reverse=True)
                team_dict[conference][division] = teams
        teams = team_dict
        self.data.update({
            'teams': teams
        })
        return self.data
        
    @view_config(route_name='league_standings_view',
                 renderer='bizarro.templates:league/standings/league.jinja2',
                 match_param='view_type=league')
    def standings_league(self):
        key = lambda x: x['home_wins'] + x['away_wins']
        teams = sorted(list(self.teams), key=key, reverse=True)
        self.data.update({
            'teams': teams,
        })
        return self.data
        
    @view_config(route_name='league_standings_view',
             renderer='bizarro.templates:league/standings/conference.jinja2',
             match_param='view_type=conference')
    def standings_conference(self):
        key = lambda x: x['Team'].division.conference
        teams = groupby(sorted(list(self.teams), key=key), key=key)
        key = lambda x: x['home_wins'] + x['away_wins']
        c_teams = {conference: sorted(list(t_list), key=key, reverse=True) 
                    for conference, t_list in teams}
        self.data.update({
            'c_teams': c_teams,
        })
        return self.data
        
class StatView(object):

    def __init__(self, request):
        self.request = request
        self.sport = request.matchdict['sport']
        league_abbr = request.matchdict['league']
        self.league = League.get(abbr=league_abbr).one()
        self.season = int(request.GET.get('season', 2012))
        self.game_type = request.GET.get('game_type', 'reg')
        self.data = {
            'sport': self.sport,
            'league': self.league,
            'season_year': self.season,
            'game_type': self.game_type,
            'game_types': Game.game_types,
            'page': 'stats',
            'base_cats': ['rk', 'player', 'team', 'pos', 'gp']
        }

    @view_config(route_name='league_stats', 
                 renderer='bizarro.templates:league/stats.jinja2',
                 match_param='sport=basketball')
    def basketball_stats(self):
        self.stat_type = self.request.GET.get('stat_type', 'game')
        Stat = BasketballBoxScoreStat
        models = [Stat]
        queries = [(model, model.sum_query()) for model in models]
        info = {
            'game_type': self.game_type,
            'sport': self.sport,
            'season': self.season,
            'league': self.league,
            'queries': queries,
            'q': 'min',
        }
        players = Player.stats(**info)
        stat_types = ['game', 'season', '36']
        players = Stat.calc_add(players, self.stat_type)
        self.data.update({
            'players': players,
            'stat_type': self.stat_type,
            'stat_types': stat_types,
            'cats': Stat.full_cats()
        })
        return self.data
    
    @view_config(route_name='league_stats', 
                 renderer='bizarro.templates:league/stats.jinja2',
                 match_param='sport=football')
    def football_stats(self):
        self.stat_type = self.request.GET.get('stat_type', 'passing') 
        map_ = PlayerStat.model_map(sport=self.sport)
        model = map_[self.stat_type]
        q, query = model.sum_query(stat_type=self.stat_type)
        queries = [(model, query)]
        q_info = {
            'game_type': self.game_type,
            'season': self.season,
            'sport': self.sport,
            'league': self.league,
            'queries': queries,
            'q': q
        }
        players = Player.stats(**q_info).all()
        players, cats = model.calc_additional(players, self.stat_type)
        stat_types = map_.keys()
        self.data.update({
            'cats': cats,
            'stat_type': self.stat_type,
            'players': players,
            'stat_types': stat_types,
        })
        return self.data
        
        
        
        
