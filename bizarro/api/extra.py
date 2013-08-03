"""
@view_config(route_name='fantasy_projections', 
                 renderer='bizarro.templates:fantasy/projections.jinja2')
def projections(self):
    request = self.request
    session = DBSession()
    page = 'projections'
    season_year = int(self.request.GET.get('season', 2011))
    source_name = request.GET.get('source_name', 'espn')
    league_info = self.data['league_info']
    team_keepers = {}
    player_keepers = {}
    #Set get variables
    if 'keeper' in str(request.GET):
        for item in request.GET.keys():
            if 'id' in item:
                id_ = int(request.GET[item])
                value = int(request.GET[item.replace('id', 'val')])
                if 'player' in item:
                    player_keepers[id_] = value
                elif 'team' in item:
                    team_keepers[id_] = value
    if 'league_size' in request.GET:
        league_info['players'] = int(request.GET['league_size'])
    if 'budget' in request.GET:
        league_info['budget'] = int(request.GET['budget'])
    for cat, scoring in league_info['scoring'].items():
        for item, value in scoring.items():
            if item in request.GET:
                league_info['scoring'][cat][item] = float(request.GET[item])
    #Calculate roster size
    roster_size = 0
    for k,v in league_info['roster'].items():
        if not k == 'flex':
            if k in request.GET:
                league_info['roster'][k] = int(request.GET[k])
    for k, v in league_info['roster'].items():
        if k == 'flex':
            roster_size += len(league_info['roster']['flex'])
        else:
            roster_size += v
    #All projections
    '''
    ps = {
        'kicking': FootballKickingProjection,
        'offense': FootballOffenseProjection,
        'defense': TeamDefenseProjection
    }
    for p_type, model in ps.items():
        q = session.query(model)
        if p_type == 'defense':
            q = q.options(eagerload('team'), 
                          eagerload('team.league'))
                          
        else:
            q = q.options(eagerload('player'),
                          eagerload('player.positions'),
                          eagerload('player.league'),
                          eagerload('player.team'))
        ps[p_type] = q.join(Projection, League, Season)\
                      .filter(Projection.source_name==source_name,
                              Season.year==season_year,
                              League.abbr==self.league.abbr)
    '''
    proj = session.query(Projection)\
                  .options(eagerload('projections'))\
                  .join(League, Season)\
                  .filter(Projection.source_name==source_name,
                          Season.year==season_year,
                          League.abbr==self.league.abbr)
    ps = proj.projections
    #Calculate Fantasy Points
    scoring = league_info['scoring']
    ps = [fantasy.calc_proj_pts(player, scoring) for player in ps]
    '''
    for p_type, players in ps.items():
        p_list = []
        for player in players:
            p = player.as_dict()
            score = 0
            if p_type == 'offense':
                for k, v in scoring['offense'].items():
                    if p[k]:
                        score += p[k] * v
                p['fantasy_points'] = score
            elif p_type == 'kicking':
                score += p['xp_make'] * scoring['kicking']['xp_made']
                score += p['xp_miss'] * scoring['kicking']['xp_miss']
                fg_made = p['b_40_50_make'] + p['u_40_make']
                score += fg_made * scoring['kicking']['fg_made']
                score += p['o_50_make'] * scoring['kicking']['50_made']
                p['fantasy_points'] = score
            if p_type == 'defense':
                p.pop('team_id')
                p['team'] = player.team
            else:
                p.pop('player_id')
                p['player'] = player.player
            p_list.append(p)
        ps[p_type] = p_list
    '''
    #For each position, find baseline
    roster = copy.deepcopy(league_info['roster'])
    roster.pop('bench')
    flex = roster.pop('flex')
    f = {}
    for item in flex:
        for pos in item:
            if pos in f:
                f[pos] += 1
            else:
                f[pos] = 1
    flex_players = []
    #Sort into dict of players by positions, find baselines
    extra = len(flex) * league_info['players']
    for pos, v in roster.items():
        if pos == 'pk':
            pos_ps = ps['kicking']
        elif pos == 'def':
            pos_ps = ps['defense']
        else:
            pos_ps = [p for p in ps['offense']
                        if pos in p['player'].position_string()]
        pos_ps = sorted(pos_ps, 
                        key=lambda x: x['fantasy_points'], 
                        reverse=True)
        multiplier = 1.2
        baseline = league_info['players'] * roster[pos] * multiplier - 1
        baseline = int(math.ceil(baseline))
        if pos == 'def':
            baseline = 1
        elif pos == 'pk':
            baseline = 0
        roster[pos] = {}
        roster[pos]['players'] = pos_ps
        roster[pos]['baseline'] = baseline
        if pos in f:
            flex_players += pos_ps[baseline:baseline+extra]
    flex_players = sorted(flex_players, 
                          key=lambda x: x['fantasy_points'], 
                          reverse=True)
    #Add flex players to baselines
    flex_players = flex_players[:extra]
    for p in flex_players:
        pos = p['player'].positions[0].abbr
        if pos not in roster:
            for pos in p['player'].positions:
                if pos.abbr in roster:
                    pos = pos.abbr
                    break
                else:
                    pos = None
        roster[pos]['baseline'] += 1
    for pos, v in roster.items():
        print pos, ' : ', v['baseline']
    extra_dollars = (league_info['budget'] - 
                        roster_size) * league_info['players']
    total_alpha = 0
    for pos, v in roster.items():
        baseline = v['players'][v['baseline']]['fantasy_points']
        for p in v['players'][:v['baseline']]:
            total_alpha += p['fantasy_points'] - baseline
    projections = []
    def calc_alpha(p, pos):
        baseline = roster[pos]['baseline']
        baseline_points = roster[pos]['players'][baseline]['fantasy_points']
        alpha = p['fantasy_points'] - baseline_points
        return alpha
    old_ppd = extra_dollars/total_alpha
    for proj_type, players in ps.items():
        for num, p in enumerate(players):
            add = True
            if proj_type == 'defense':
                alpha = calc_alpha(p, 'def')              
                p['alpha'] = int(math.ceil(alpha))
                if team_keepers and p['team'].id in team_keepers:
                    extra_dollars -= team_keepers[p['team'].id]
                    total_alpha -= alpha
                    p['keeper_value'] = team_keepers[p['team'].id]        
                    team_keepers[p['team'].id] = p
                    add = False
            else:
                alpha = None
                for pos in p['player'].positions:
                    pos = pos.abbr
                    if pos in roster and (calc_alpha(p, pos) > alpha or 
                                          not alpha):
                        alpha = calc_alpha(p, pos)
                p['alpha'] = int(math.ceil(alpha))
                if player_keepers and p['player'].id in player_keepers:
                    extra_dollars -= player_keepers[p['player'].id]
                    total_alpha -= alpha
                    p['keeper_value'] = player_keepers[p['player'].id]
                    player_keepers[p['player'].id] = p
                    add = False
            if add:
                projections.append(p)
    ppd = extra_dollars/total_alpha
    projections = sorted(projections, 
                         key=lambda x: x['alpha'], 
                         reverse=True)
    sources = session.query(Source)\
                     .join(Projection)\
                     .all()
    teams = session.query(Team)\
                   .join(LeagueTeam)\
                   .filter(LeagueTeam.league_id==self.league.id)\
                   .all()
    positions = ['qb', 'rb', 'wr', 'te', 'pk', 'd/st']
    self.data.update({
        'projections': projections,
        'sources': sources,
        'source_name': source_name,
        'teams': teams,
        'positions': positions,
        'team_keepers': team_keepers,
        'player_keepers': player_keepers,
        'keepers': team_keepers.values() + player_keepers.values(),
        'old_ppd': old_ppd,
        'ppd': ppd,
        'ps': ps,
        'page': page,
    })
    return self.data
"""
