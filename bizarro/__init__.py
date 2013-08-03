from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base
    )
    
    
def routes(config):
    #Home Pages
    config.add_route('home', '/',)
    #League
    config.add_route('league_home', '/{sport}/{league}/')
    config.add_route('league_teams', '/{sport}/{league}/teams/')
    config.add_route('league_scores', '/{sport}/{league}/scores/')
    config.add_route('league_schedule', '/{sport}/{league}/schedule/')
    config.add_route('league_standings', '/{sport}/{league}/standings/')
    config.add_route('league_standings_view', '/{sport}/{league}/standings/{view_type}/')    
    config.add_route('league_rankings', '/{sport}/{league}/rankings/')
    config.add_route('league_players', '/{sport}/{league}/players/')
    config.add_route('league_stats', '/{sport}/{league}/stats/')
    config.add_route('league_rumors', '/{sport}/{league}/rumors/')
    config.add_route('league_transactions', '/{sport}/{league}/transactions/')
    config.add_route('league_news', '/{sport}/{league}/news/')
    config.add_route('league_injuries', '/{sport}/{league}/injuries/')
    config.add_route('league_odds', '/{sport}/{league}/odds/')
    #Teams
    config.add_route('team_home', '/{sport}/{league}/teams/{team_abbr}/')
    config.add_route('team_roster', 
                      '/{sport}/{league}/teams/{team_abbr}/roster/')
    config.add_route('team_schedule', 
                     '/{sport}/{league}/teams/{team_abbr}/schedule/')
    config.add_route('team_news', 
                     '/{sport}/{league}/teams/{team_abbr}/news/')
    config.add_route('team_stats', 
                     '/{sport}/{league}/teams/{team_abbr}/stats/')
    config.add_route('team_splits', 
                     '/{sport}/{league}/teams/{team_abbr}/splits/')
    config.add_route('team_depth_chart', 
                     '/{sport}/{league}/teams/{team_abbr}/depth_chart/')
    config.add_route('team_rankings', 
                     '/{sport}/{league}/teams/{team_abbr}/rankings/')
    config.add_route('team_transactions', 
                     '/{sport}/{league}/teams/{team_abbr}/transactions/')
    config.add_route('team_photos', 
                     '/{sport}/{league}/teams/{team_abbr}/media/')
    config.add_route('team_stadium', 
                     '/{sport}/{league}/teams/{team_abbr}/stadium/')
    config.add_route('team_forum', 
                     '/{sport}/{league}/teams/{team_abbr}/forum/')
    config.add_route('team_shots', 
                     '/{sport}/{league}/teams/{team_abbr}/shots/')
    #Players
    config.add_route('players', 
                     '/{sport}/{league}/players/')
    config.add_route('player', 
        '/{sport}/{league}/player/{player_id}/{player_name}/')
    config.add_route('player_stat', 
        '/{sport}/{league}/player/{player_id}/{player_name}/stats/')
    config.add_route('player_shots', 
        '/{sport}/{league}/player/{player_id}/{player_name}/shots/')
    config.add_route('player_projections', 
        '/{sport}/{league}/player/{player_id}/{player_name}/projections/')
    #Games
    config.add_route('game', '/{sport}/{league}/games/{game_id}/') 
    config.add_route('game_boxscore', 
                     '/{sport}/{league}/games/{game_id}/boxscore/')
    config.add_route('game_plays', '/{sport}/{league}/games/{game_id}/plays/')
    config.add_route('game_shots', '/basketball/nba/games/{game_id}/shots/')
    #Fantasy
    config.add_route('fantasy_home', '/{sport}/{league}/fantasy/')
    config.add_route('fantasy_home1', '/{sport}/{league}/fantasy/home/')
    config.add_route('fantasy_players', '/{sport}/{league}/fantasy/players/')
    config.add_route('fantasy_players_stat_type', '/{sport}/{league}/fantasy/players/{stat_type}/')
    config.add_route('fantasy_rankings', '/{sport}/{league}/fantasy/rankings/')
    config.add_route('fantasy_stats', '/{sport}/{league}/fantasy/stats/')
    config.add_route('fantasy_stats_weekly', '/{sport}/{league}/fantasy/stats/weekly/')
    config.add_route('fantasy_projections', '/{sport}/{league}/fantasy/projections/')
    config.add_route('fantasy_projections_user', '/{sport}/{league}/fantasy/projections/user/')
    config.add_route('fantasy_projections_json', '/{sport}/{league}/fantasy/projections/json/')
    config.add_route('fantasy_cheatsheet', '/{sport}/{league}/fantasy/projections/cheatsheet/')
    config.add_route('fantasy_cheatsheet_xls', '/{sport}/{league}/fantasy/projections/cheatsheet/xls/')
    config.add_route('fantasy_cheatsheet_save', '/{sport}/{league}/fantasy/projections/cheatsheet/save/')
    config.add_route('test_backbone', '/football/nfl/fantasy/backbone/')
    config.add_renderer(name='csv',
                        factory='bizarro.renderers.CSVRendererFactory')
    config.add_renderer(name='xls',
                        factory='bizarro.renderers.XLSRendererFactory')
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    settings['reload_all'] = True
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.include(routes)
    config.include('pyramid_jinja2')
    config.include('apex', route_prefix='/auth')
    config.scan()
    return config.make_wsgi_app()
