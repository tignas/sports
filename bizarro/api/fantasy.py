import json
import math
import copy
from itertools import groupby
from collections import OrderedDict
from sqlalchemy.orm import aliased, eagerload
from bizarro.models.teams import Team, LeagueTeam, League
from bizarro.models.people import Player, PlayerPosition, Position, TeamPlayer
from bizarro.models.stats import Game, Season, BasketballBoxScoreStat, FootballKickingStat, PlayerStat, GamePlayer, FootballOffensiveStat
from bizarro.models.fantasy import Projection, FootballOffenseProjection, FootballKickingProjection, TeamDefenseProjection
from bizarro.api.sums import sum_request, model_map, average_request
from connect_db import create_session

def req_vars(request, league_info):
    session = create_session()
    season_year = int(request.GET.get('season', 2013))
    proj_ids = request.params.getall('proj')
    if proj_ids:
        proj_ids = [int(p_id) for p_id in proj_ids]
    else:
        proj_ids = [session.query(Projection).first().id]
    writer_name = request.GET.get('writer_name', '')
    keepers = {}
    if 'keeper' in str(request.GET):
        for k, v in request.GET.iteritems():
            if 'keeper' in k:
                pid = int(k.split('_')[1])
                keepers[pid] = int(v)
    if 'base' in str(request.GET):
        base = OrderedDict()
        for k, v in request.GET.iteritems():
            if 'base' in k:
                pos = k.split('_')[1]
                base[pos] = {}
                base[pos]['baseline'] = int(v) - 1
        league_info['baselines'] = base
    if 'league_size' in request.GET:
        league_info['owners'] = int(request.GET['league_size'])
    if 'budget' in request.GET:
        league_info['budget'] = int(request.GET['budget'])
    for cat, scoring in league_info['scoring'].iteritems():
        for item, value in scoring.iteritems():
            if cat == 'offense':
                for k, v in value.iteritems():
                    s = item + '_' + k
                    if s in request.GET:
                        league_info['scoring'][cat][item][k] = float(request.GET[s])
            else:
                if item in request.GET:
                    league_info['scoring'][cat][item] = float(request.GET[item])
    for k,v in league_info['roster'].iteritems():
        if not k == 'flex':
            if k in request.GET:
                league_info['roster'][k] = int(request.GET[k])
        else:
            if 'flex_num' in request.GET:
                flex_num = int(request.GET['flex_num'])
                if flex_num:
                    flex_pos = request.params.getall('flex')
                    flex = [flex_pos for i in range(flex_num)]
                    league_info['roster']['flex'] = flex
                else:
                    del league_info['roster']['flex']
    vars_ =  season_year, proj_ids, writer_name, keepers, league_info
    return vars_

def stats(league_abbr, season_year, game_type, stat_type):
    session = create_session()
    league_info = fantasy_league(league_abbr)
    if league_abbr == 'nfl':
        map_ = model_map('football')['fantasy'][stat_type]
        if stat_type == 'defense':
            players = session.query(Team)\
                             .join(LeagueTeam, League)\
                             .filter(League.id==1)\
                             .all()
        elif stat_type in ['offense', 'kicking']:
            stats = []
            for model in map_['models']:
                model, sum_query = sum_request(model)
                stat = session.query(model.player_id, *sum_query)\
                              .join(Game, Season)\
                              .filter(Game.game_type==game_type,
                                      Season.year==season_year)\
                              .group_by(model.player_id)\
                              .subquery()
                stats.append(stat)
            q = session.query(Player, *stats)\
                       .join(PlayerPosition, Position, TeamPlayer)
            for stat in stats:
                q = q.outerjoin(stat)
            players = q.filter(Position.abbr.in_(map_['positions']),
                               Player.league_id==1)\
                       .group_by(Player)\
                       .having(stats[0].c.gp>0)
        elif stat_type == 'defense':
            pass
    elif league_abbr == 'nba':
        Stat, sum_query = sum_request(BasketballBoxScoreStat)
        stats = session.query(Stat.player_id, *sum_query)\
                       .join(Game, Season)\
                       .filter(Game.game_type==game_type, 
                               Season.year==season_year)\
                       .group_by(Stat.player_id)\
                       .subquery()
        players = session.query(Player, Team, stats)\
                         .options(eagerload('positions'),
                                  eagerload(Team.league))\
                         .join(TeamPlayer, Team)\
                         .outerjoin(stats)\
                         .group_by(Player)\
                         .having(stats.c.gp > 0)
    return players
    
def stats_weekly(league_abbr, season_year, game_type, stat_type):
    session = create_session()
    league_info = fantasy_league(league_abbr)
    map_ = model_map('football')['fantasy'][stat_type]
    positions = map_['positions']
    if stat_type in ['offense', 'kicking']:
        '''
        get stats for each player for each week
        '''      
        players = session.query(FootballOffensiveStat)\
                   .options(eagerload('player'),
                            eagerload('player.positions'),
                            eagerload('player.league'))\
                   .join(Player, Game, Season)\
                   .filter(Season.year==2012, Game.game_type=='reg',
                          Player.positions.any(Position.abbr.in_(positions)))
    return players
   
def player_pos(player):
    pos_list = player.position_string().split('/')
    if len(pos_list) > 1:
        for pos in ['te', 'rb', 'wr', 'qb']:
            if pos in pos_list:
                break
    else:
        pos = pos_list[0]
    return pos
    
def calc_auction(ps, league_info):
    key = lambda x: x['fantasy_points']
    ps = sorted(ps, key=key, reverse=True)
    #For each position, find baseline
    roster = copy.deepcopy(league_info['roster'])
    flex = roster.pop('flex', [])
    del roster['bench']
    #Calculate baseline number player
    if 'baselines' in league_info:
        baselines = league_info['baselines']
    else:
        mult = 1
        baselines = calc_base(league_info['owners'], roster, mult)
        if flex:
            baselines = adjust_flex_baseline(league_info, ps, baselines, flex)
    positions = roster.keys()
    extra_dollars = calc_extra_dollars(league_info)
    roster, total_alpha = calc_alpha(baselines, ps)
    for num, p in enumerate(ps):
        alpha = p['fantasy_points'] - roster[p['position']]['baseline_pts']
        ps[num]['alpha'] = alpha
    key = lambda x: x['alpha']
    ps = sorted(ps, key=key, reverse=True)
    return ps, total_alpha, extra_dollars, positions, roster
    
def calc_pts(players, scoring, stat_type):
    player_points = []
    points_min = 35
    if stat_type == 'offense':
        for p in players:
            player = p._asdict()
            player['position'] = player_pos(player['Player'])
            points = 0
            for cat, items in scoring[stat_type].iteritems():
                for item, val in items.iteritems():
                    cat_name = cat + '_' + item
                    if cat_name in player and player[cat_name]:
                        points += player[cat_name] * val
            if points > points_min:
                player['fantasy_points'] = points
                player_points.append(player)
    elif stat_type == 'kicking':
        for player in players:
            player = player._asdict()
            points = 0
            try:
                points += player['fg_made'] * scoring['kicking']['fg_made']
                points += player['xp_made'] * scoring['kicking']['xp_made']
                points += (player['xp_attempts'] - player['xp_made']) * \
                           scoring['kicking']['xp_miss']
            except TypeError:
                pass
            if points > points_min:
                player['fantasy_points'] = points
                player['position'] = 'pk'
                player_points.append(player)
    elif stat_type == 'defense':
        for p in players:
            player = {}
            player['fantasy_points'] = 100
            player['position'] = 'def'
            player_points.append(player)
    return player_points
    
def calc_pts_json(players, scoring, stat_type):
    player_list = []
    for p in players:
        player = p._asdict()
        fantasy_points = 0
        for cat, val in scoring.iteritems():
            if stat_type == 'offense':
                for item, v in val.iteritems():
                    cat_name = cat + '_' + item
                    if player[cat_name]:
                        fantasy_points += player[cat_name]*v
            elif player[cat]:
                fantasy_points += player[cat]*val
        player['fantasy_points'] = fantasy_points
        this_player = player.pop('Player')
        team = this_player.team
        player['team'] = {
            'name': team.name,
            'abbr': team.abbr,
            'id': team.id
        }
        player['player'] = {
            'id': this_player.id,
            'name': this_player.person.names[0].full_name,
            'position': player_pos(this_player)
        }
        if fantasy_points > 0:
            player_list.append(player)
    return player_list
    
def calc_pts_json_weekly(stats, scoring, stat_type):
    stat_list = []
    for s in stats:
        player = s.player
        game = s.game
        s = s.as_dict()
        fantasy_points = 0
        for cat, val in scoring.iteritems():
            if stat_type == 'offense':
                for item, v in val.iteritems():
                    cat_name = cat + '_' + item
                    try:
                        if s[cat_name]:
                            fantasy_points += s[cat_name]*v
                    except KeyError:
                        bad = {
                            'fumbles_total': 'fumble_fumbles',
                            'fumbles_recovered': 'fumble_recovered',
                            'fumbles_lost': 'fumble_lost'
                        }
                        if 'fumble' in cat_name:
                            cat_name = bad[cat_name]
                        if 'return' in cat_name:
                            for i in ['punt', 'kick']:
                                c = '%s_%s' % (i, cat_name)
                                if s[c]:
                                    fantasy_points += s[c]*v
                        else:
                            if s[cat_name]:
                                fantasy_points += s[cat_name]*v
            elif s[cat]:
                fantasy_points += s[cat]*val
        s['fantasy_points'] = fantasy_points
        s['player'] = player
        s['game'] = game
        s['week'] = game.week()
        if fantasy_points > 0:
            stat_list.append(s)
    return stat_list
    
def calc_proj_pts(players, scoring):
    p_list = []
    for player in players:
        p = player._asdict()
        p_type = p['p_type']
        score = 0
        if p_type == 'offense':
                for cat, items in scoring['offense'].iteritems():
                    for item, val in items.iteritems():
                        cat_name = cat + '_' + item
                        if p[cat_name]:
                            score += p[cat_name] * val
        elif p_type == 'kicking':
            score += p['xp_make'] * scoring['kicking']['xp_made']
            score += p['xp_miss'] * scoring['kicking']['xp_miss']
            fg_made = p['b_40_50_make'] + p['u_40_make']
            score += fg_made * scoring['kicking']['fg_made']
            score += p['o_50_make'] * scoring['kicking']['50_made']
        if p_type == 'defense':
            p['fantasy_points'] = round(p['fantasy_points'], 2)
            p['position'] = 'def'
        else:
            p['fantasy_points'] = round(score, 2)
            if p_type == 'offense':
                p['position'] = player_pos(p['Player'])
            elif p_type == 'kicking':
                p['position'] = 'pk'
        if p['fantasy_points'] > 40:
            p_list.append(p)
    return p_list
    
def roster_size(roster):
    size = 0
    for k, v in roster.iteritems():
        if k == 'flex':
            size += len(roster['flex'])
        else:
            size += v
    return size

def flex_to_dict(flex):
    f = {}
    for item in flex:
        for pos in item:
            if pos in f:
                f[pos] += 1
            else:
                f[pos] = 1
    return f
    
def calc_base(num_players, roster, multiplier):
    for pos, v in roster.iteritems():
        if pos == 'def':
            baseline = 1
        elif pos == 'pk':
            baseline = 0
        else:
            baseline = num_players * roster[pos] * multiplier - 1
        baseline = int(math.ceil(baseline))
        roster[pos] = {}
        roster[pos]['baseline'] = baseline
    return roster
    
def adjust_flex_baseline(league_info, ps, roster, flex):
    extra = len(flex) * league_info['owners']
    flex_dict = flex_to_dict(flex)
    flex_ps = []
    for pos, v in flex_dict.iteritems():
        baseline = roster[pos]['baseline']
        pos_ps = [p for p in ps if p['position'] == pos]
        flex_ps += pos_ps[baseline:baseline+extra]
    flex_baseline = len(flex) * league_info['owners']
    key = lambda x: x['fantasy_points']
    flex_ps = sorted(flex_ps, key=key, reverse=True)
    flex_ps = flex_ps[:flex_baseline]
    for p in flex_ps:
        roster[p['position']]['baseline'] += 1
    return roster
    
def calc_extra_dollars(league_info):
    po = (league_info['budget'] - roster_size(league_info['roster']))
    ed = po * league_info['owners']
    return ed
    
def calc_alpha(roster, ps):
    a = 0
    for pos, v in roster.iteritems():
        pos_ps = [p for p in ps if p['position'] == pos]
        baseline = roster[pos]['baseline']
        try:
            base_pts = pos_ps[baseline]['fantasy_points']
        except IndexError:
            print pos
            raise Exception('hello')
        roster[pos]['baseline_pts'] = base_pts
        for p in pos_ps[:baseline]:
            a += p['fantasy_points'] - base_pts
    return (roster, a)
    
def calc_rank_val(baselines, players, ppd):
    pos_ranks = {pos:1 for pos in baselines.keys()}
    for n, p in enumerate(players):
        if p['alpha'] > 0:
            value = p['alpha'] * ppd + 1
            value = int(round(value))
        else:
            value = 1
        players[n].update({
            'value': value,
            'rank': pos_ranks[p['position']]
        })
        pos_ranks[p['position']] += 1
    return players
    
def calc_dollars(total_alpha, extra_dollars, keepers, players):
    old_ppd = extra_dollars/total_alpha
    if keepers:
        for p in players:
            if 'Player' in p and p['Player'].id in keepers:
                extra_dollars -= keepers[p['Player'].id]
                total_alpha -= p['alpha']
        ppd = extra_dollars/total_alpha
    else:
        ppd = old_ppd
    return ppd, old_ppd, extra_dollars, total_alpha
    
def proj_players(proj_ids, season_year, league_abbr):
    session = create_session()
    players = []
    models = [FootballOffenseProjection, FootballKickingProjection]
    for model in models:
        Stat, avg_query = average_request(model)
        p_query = session.query(Player,  Stat.projection_type.label('p_type'),
                                *avg_query)\
                          .join(Stat, Projection, League, Season)\
                          .filter(Projection.id.in_(proj_ids),
                                  Season.year==season_year,
                                  League.abbr==league_abbr)\
                          .group_by(Stat.player_id)\
                          .all()
        players.extend(p_query)
    Stat, avg_query = average_request(TeamDefenseProjection)
    t_query = session.query(Team, Stat.projection_type.label('p_type'),
                            *avg_query)\
                      .join(Stat, Projection, League, Season)\
                      .filter(Projection.id.in_(proj_ids),
                              Season.year==season_year,
                              League.abbr==league_abbr)\
                       .group_by(Stat.team_id)\
                       .all()
    players.extend(t_query)
    return players
    
def calc_projections(request, league_info, league_abbr):
    vars_ = req_vars(request, league_info)
    season_year, proj_ids, writer_name, keepers, league_info = vars_
    players = proj_players(proj_ids, season_year, league_abbr)
    ps = calc_proj_pts(players, league_info['scoring'])
    a_info = calc_auction(ps, league_info)
    ps, total_alpha, extra_dollars, positions, baselines = a_info
    players = ps
    d_info = calc_dollars(total_alpha, extra_dollars, keepers, players)
    ppd, old_ppd, extra_dollars, total_alpha = d_info
    players = calc_rank_val(baselines, players, ppd)
    data = {
        'league_info': league_info,
        'players': players,
        'proj_ids': proj_ids,
        'keepers': keepers,
        'extra_dollars': extra_dollars,
        'total_alpha': total_alpha,
        'old_ppd': old_ppd,
        'ppd': ppd,
        'season_year': season_year,
        'baselines': baselines,
        'positions': baselines.keys()
    }
    return data
    
def fantasy_league(league):
    if league == 'nfl':
        league_info = OrderedDict([
            ('owners', 12),
            ('budget', 200),
            ('roster',  OrderedDict([
                ('qb', 1),
                ('rb', 2),
                ('wr', 3),
                ('te', 1),
                ('pk', 1),
                ('def', 1),
                ('bench', 7),
                ('flex', [
                    ['rb', 'wr', 'te'],
                ]),
            ])),
            ('scoring', OrderedDict([
                ('offense', OrderedDict([
                    ('passing', OrderedDict([
                        ('attempts', 0),
                        ('completions', 0),
                        ('yards', 0.04),
                        ('touchdowns', 4),
                        ('interceptions', -2),
                        ('sacks', 0),
                    ])),
                    ('rushing', OrderedDict([
                        ('attempts', 0),
                        ('yards', .1),
                        ('touchdowns', 6),
                    ])),
                    ('receiving', OrderedDict([
                        ('receptions', 0),
                        ('yards', 0.1),
                        ('touchdowns', 6),
                    ])),
                    ('fumbles', OrderedDict([
                        ('total', 0),
                        ('lost', -2),
                    ])),
                    ('return', OrderedDict([
                        ('yards', 0),
                        ('touchdowns', 6)
                    ])),
                ])),
                ('kicking', OrderedDict([
                    ('xp_made', 1),
                    ('xp_miss', -2),
                    ('fg_made', 3),
                    ('50_made', 4),
                ])),
                ('defense', OrderedDict([
                    ('interceptions', 2),
                    ('touchdowns', 6),
                    ('fumbles_recovered', 1),
                    ('safeties', 2),
                    ('sacks', 1),
                ]))
            ]))
        ])
    elif league == 'nba':
        league_info = {}
    return league_info
