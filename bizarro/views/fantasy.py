import json
import copy
import math
import datetime
import time
import csv
import xlwt
import tablib
import numpy
import transaction
from itertools import groupby, ifilter
from collections import OrderedDict
from pyramid.view import view_config
from pyramid.renderers import render_to_response, Response
from pyramid.response import FileResponse
from sqlalchemy.orm import aliased, eagerload, joinedload, subqueryload
from sqlalchemy import and_, or_, desc, func
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.media import *
from bizarro.models.fantasy import *
from bizarro.api import fantasy as f
from bizarro.api.sums import *

class FantasyView(object):

    def __init__(self, request):
        page = request.matched_route.name.split('_')[1]
        self.request = request
        self.league = League.get(abbr=request.matchdict['league']).one()
        self.sport = request.matchdict['sport']
        self.data = {
            'league': self.league,
            'sport': self.sport,
            'league_info': f.fantasy_league(self.league.abbr)
        }
        
    @view_config(route_name='fantasy_home1',
                 renderer='bizarro.templates:fantasy/home.jinja2')
    @view_config(route_name='fantasy_home',
                 renderer='bizarro.templates:fantasy/home.jinja2')
    def home(self):
        return self.data
        
    @view_config(route_name='fantasy_players',
                 renderer='bizarro.templates:fantasy/players.jinja2')
    def players(self):
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2013))
        player_stats = {stat_type: f.stats(self.league.abbr, season_year, 
                                           game_type, stat_type)
                        for stat_type in ['offense', 'kicking', 'defense']}
        league_info = self.data['league_info']
        for cat, scoring in league_info['scoring'].iteritems():
            for item, value in scoring.iteritems():
                if cat == 'offense':
                    for k, v in value.iteritems():
                        s = item + '_' + k
                        if s in self.request.GET:
                            league_info['scoring'][cat][item][k] = float(self.request.GET[s])
                else:
                    if item in self.request.GET:
                        league_info['scoring'][cat][item] = float(self.request.GET[item])
        players = []
        for pos, val in league_info['roster'].iteritems():
            if not pos == 'flex' and pos in self.request.GET:
                league_info['roster'][pos] = int(self.request.GET[pos])
        for stat_type, p_list in player_stats.iteritems():
            players += f.calc_pts(p_list, league_info['scoring'], stat_type)
        a_info = f.calc_auction(players, league_info)
        players, alpha, extra_dollars, positions, baselines = a_info
        teams = Team.get(league=self.league).all()
        self.data.update({
            'players': players,
            'game_type': game_type,
            'season_year': season_year,
            'teams': teams,
            'positions': positions,
            'alpha': alpha,
            'baselines': baselines,
            'extra_dollars': extra_dollars,
            'ppd': extra_dollars/alpha
        })
        return self.data
        
    @view_config(route_name='fantasy_players_stat_type',
                 renderer='bizarro.templates:fantasy/players_stat_type.jinja2')
    def players_stat_type(self):
        session = DBSession()
        page = 'players'
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2011))
        stat_type = self.request.matchdict['stat_type']
        players = f.stats(self.league.abbr, season_year, game_type, stat_type)
        scoring = self.data['league_info']['scoring']
        players = f.calc_pts(self.league.abbr, players, scoring, stat_type)
        self.data.update({
            'players': players,
            'scoring': scoring,
            'stat_type': stat_type
        })
        return self.data

    @view_config(route_name='fantasy_stats', 
                 renderer='bizarro.templates:fantasy/stats.jinja2')
    def stats(self):
        session = DBSession()
        page = 'stats'
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2011))
        stat_type = 'offense'
        scoring = self.data['league_info']['scoring'][stat_type]
        for category in scoring.keys():
            if self.request.GET.has_key(category):
                scoring[category] = float(self.request.GET[category])
        players = f.stats(self.league.abbr, season_year, game_type, stat_type)
        players = f.calc_pts_json(players, scoring, stat_type)
        key = lambda x: x['fantasy_points']
        players = sorted(players, key=key, reverse=True)
        players = players[0:200]
        self.data.update({
            'positions': ['qb', 'rb', 'wr', 'te'],
            'players': players,
            'game_type': game_type,
            'scoring': scoring,
            'season': season_year,
            'page': page,
            'json_players': json.dumps(players)
        })
        return self.data
        
    @view_config(route_name='fantasy_stats_weekly', 
                 renderer='bizarro.templates:fantasy/stats_weekly.jinja2')
    def stats_weekly(self):
        session = DBSession()
        page = 'stats_weekly'
        game_type = self.request.GET.get('game_type', 'reg')
        season_year = int(self.request.GET.get('season', 2012))
        stat_type = 'offense'
        scoring = self.data['league_info']['scoring'][stat_type]
        for category in scoring.keys():
            if self.request.GET.has_key(category):
                scoring[category] = float(self.request.GET[category])
        #players = f.stats_weekly(self.league.abbr, season_year, game_type, 
        #                         stat_type)
        positions = ['qb', 'rb', 'wr', 'te']
        positions = positions[1:2]
        stats = session.query(FootballOffensiveStat)\
                   .options(eagerload('player'),
                            eagerload('player.positions'),
                            eagerload('player.league'),
                            eagerload('game'),
                            eagerload('game.season'))\
                   .join(Player, Game, Season)\
                   .filter(Season.year==season_year, Game.game_type=='reg',
                          Player.positions.any(Position.abbr.in_(positions)))
        stats = f.calc_pts_json_weekly(stats, scoring, stat_type)
        key = lambda x: x['player']
        stats_by_player = groupby(sorted(stats, key=key), key=key)
        players = []
        for p, stats in stats_by_player:
            weeks = [None for w in range(17)]
            total_points = 0
            pts = []
            stud = 0
            bust = 0
            avg = 0
            gp = 0
            for stat in stats:
                gp += 1
                weeks[stat['week']-1] = stat
                total_points += stat['fantasy_points']
                pts.append(stat['fantasy_points'])
                if stat['fantasy_points'] < 8:
                    bust += 1
                elif stat['fantasy_points'] > 16:
                    stud += 1
                else:
                    avg += 1
            player = {
                'player': p,
                'total_points': total_points,
                'stats': weeks,
                'mean': round(numpy.mean(pts), 1),
                'std': round(numpy.std(pts), 1),
                'stud': stud,
                'bust': bust,
                'avg': avg,
                'gp': gp,
            }
            if player['total_points'] > 30:
                players.append(player)
        key = lambda x: x['total_points']
        players = sorted(players, key=key, reverse=True)
        self.data.update({
            'positions': ['qb', 'rb', 'wr', 'te'],
            'players': players,
            'game_type': game_type,
            'scoring': scoring,
            'season': season_year,
            'page': page,
            'weeks': list(range(1, 18))
        })
        return self.data
        
    @view_config(route_name='fantasy_cheatsheet',
                 renderer='bizarro.templates:fantasy/cheatsheet.jinja2')
    def cheatsheet(self):
        session = DBSession()
        page = 'cheatsheet'
        p_info = f.calc_projections(self.request, self.data['league_info'], self.league.abbr)
        self.data.update(p_info)
        players = self.data['players']
        key = lambda x: x['position']
        players = sorted(players, key=key)
        players = groupby(players, key=key)
        players = {pos:list(ps) for pos, ps in players}
        self.data.update({
            'players': players,
            'page': page,
        })
        return self.data
        
    
    @view_config(route_name='fantasy_cheatsheet_xls', renderer='xls')
    def cheatsheet_xls(self):
        p_info = f.calc_projections(self.request, self.data['league_info'], self.league.abbr)
        players = p_info['players']
        p_list = []
        for rk, p in enumerate(players):
            cats = ['position', 'rank', 'fantasy_points', 
                    'value']             
            p_val = [p[cat] for cat in cats]
            p_val.insert(0, rk+1)
            if 'Player' in p:
                p_val.insert(1, p['Player'].person.names[0].full_name)
                p_val.insert(2, p['Player'].team.abbr)
            else:
                p_val.insert(1, p['Team'].__repr__())
                p_val.insert(2, p['Team'].abbr)
            p_list.append(p_val)
        players = p_list
        headers = ['rank', 'name', 'team', 'pos', 'rk', 'pts', 'value']
        filename = 'projections.xls'
        key = lambda x: x[3]
        players = groupby(sorted(players, key=key), key=key)
        players = {pos:list(ps) for pos, ps in players}
        data = tablib.Databook()
        sheet = tablib.Dataset(*p_list, headers=headers, title='all')
        data.add_sheet(sheet)
        for pos in p_info['positions']:
            sheet = tablib.Dataset(*players[pos], headers=headers, title=pos)
            data.add_sheet(sheet)
        return {
            'data': data,
            'filename': filename,
        }
        
        
    @view_config(route_name='fantasy_projections', 
                 renderer='bizarro.templates:fantasy/projections.jinja2')
    def projections(self):
        session = DBSession()
        page = 'projections'
        p_info = f.calc_projections(self.request, self.data['league_info'], 
                                    self.league.abbr)
        self.data.update(p_info)
        #Projection Sources
        season_year = 2014
        projs = session.query(Projection)\
                       .join(Season)\
                       .filter(Season.year==season_year)
        key = lambda x: x.source_name
        projs = groupby(sorted(projs, key=key), key=key)
        projs = {s_name: list(p_list) for s_name, p_list in projs}
        #All Teams
        teams = session.query(Team)\
                       .join(LeagueTeam)\
                       .filter(LeagueTeam.league_id==self.league.id)
        if 'flex' in self.data['league_info']['roster']:
            flex = json.dumps(self.data['league_info']['roster']['flex'][0])
            self.data['flex'] = flex
        self.data.update({
            'teams': teams,
            'page': page,
            'projs': projs,
        })
        return self.data
    
    @view_config(route_name='fantasy_cheatsheet_save', 
                 permission='authenticated')
    def cheatsheet_save(self):
        session = DBSession()
        user_proj = UserProjection(auth_id=self.request.user.id, 
                                   url=self.request.query_string)
        session.add(user_proj)
        transaction.commit()
        return Response('hello')
        
    @view_config(route_name='fantasy_projections_user',
                 renderer='bizarro.templates:fantasy/projections_user.jinja2',
                 permission='authenticated')
    def projections_user(self):
        session = DBSession()
        page = 'my projections'
        projs = session.query(UserProjection)\
                       .filter(UserProjection.user==self.request.user)
        self.data.update({
            'projs': projs,
            'page': page,
        })
        return self.data

    @view_config(route_name='fantasy_projections_json', 
                 renderer='json')
    def projections_json(self):
        session = DBSession()
        season_year = 2014
        projections = session.query(Projection)\
                             .options(eagerload('projections'))\
                             .join(Season)\
                             .filter(Season.year==season_year)
        projections_dict = {}
        for proj in projections:
            projection = {}
            p_list = []
            for p in proj.projections:
                p_dict = p.as_dict()
                p_dict['proj_type'] = p.projection_type
                if p.projection_type == 'defense':
                    team = p.team
                    p_dict['pos'] = 'def'
                    p_dict['name'] = team.full_name()
                    p_dict['team'] = team.abbr
                    del p_dict['team_id']
                else:
                    player = p.player
                    pos = f.player_pos(player)
                    p_dict['pos'] = pos
                    p_dict['name'] = player.person.names[0].full_name
                    p_dict['team'] = player.team.abbr
                    del p_dict['player_id']
                p_list.append(p_dict)
                del p_dict['id']
            projections_dict[proj.source_name] = p_list
        return projections_dict
        
    @view_config(route_name='fantasy_rankings',
                 renderer='bizarro.templates:fantasy/rankings.jinja2')
    def rankings(self):
        session = DBSession()
        rankings = session.query(FantasyRanking)\
                          .options(eagerload('rankings'),
                                   eagerload('rankings.player'),
                                   eagerload('rankings.player.positions'))
        self.data.update({
            'rankings': rankings
        })
        return self.data
   
@view_config(route_name='test_backbone',
             renderer='bizarro.templates:backbone.jinja2')
def test_backbone(request):
    session = DBSession()
    teams = session.query(Team).join(LeagueTeam).join(League).filter(League.abbr=='nfl').all()
    data = {'teams': teams}
    return data
                
        


