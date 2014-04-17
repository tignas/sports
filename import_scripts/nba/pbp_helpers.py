import re
from helpers import *
from pprint import pprint
from bizarro.models.play_by_play import *
from sqlalchemy.orm.exc import NoResultFound
from unstdlib.standard import get_many

def get_player(session, league_id, full_description, full_name, team=None):
    start = full_description.lower().find(full_name)
    full_name = full_description[start:start+len(full_name)]
    try:
        players = session.query(Player)\
                         .join(Person, PersonName)\
                         .filter(Player.league_id==league_id,
                                 PersonName.full_name==full_name)
        player = players.one()
    except NoResultFound:
        event = full_description.lower()
        if 'jumpball' in event or ('team' in event and 'foul' in event):
            player = None
        else:
            pprint(full_name)
            pprint(full_description)
            print team
            raise Exception('no player found')
    except MultipleResultsFound:
        multiple_players = session.query(Player)\
                           .join(TeamPlayer, Person, PersonName)\
                           .filter(Player.league_id==league_id,
                                   TeamPlayer.team_id==team.id,
                                   PersonName.full_name==full_name)
        try:
            player = multiple_players.one()
        except NoResultFound:
            print team.id
            print league_id
            pprint(full_name)
            pprint(full_description)
            print team
            print players.all()
            raise Exception('not enough players but too many this is' 
                            'confusing')
    return player
            
def get_team(game, session, league, team_identifier, full_description=None):
    #Try team_abbr
    try:
        team = session.query(Team)\
                      .filter(or_(Team.abbr==team_identifier, 
                                  Team.name==team_identifier,
                                  Team.location==team_identifier))\
                      .join(LeagueTeam)\
                      .filter(LeagueTeam.league_id==league.id)\
                      .one()
    except NoResultFound:
        try:
            team = session.query(Team)\
                          .join(TeamName, LeagueTeam)\
                          .filter(TeamName.abbr==team_identifier,
                                  LeagueTeam.league_id==league.id)\
                          .one()
        except NoResultFound:
            try:
                team = session.query(Team).join(LeagueTeam, TeamLocation)\
                              .filter(LeagueTeam.league_id==league.id,
                                      TeamLocation.name==team_identifier)\
                              .one()
            except NoResultFound:
                print full_description
                print 'no team found for %s' % team_identifier
                raise Exception('whoops')
    except MultipleResultsFound:
        if team_identifier == 'los angeles':
            if (game.home_team.location == 'los angeles' and 
                game.away_team.location == 'los angeles'):
                raise Exception('both teams los angeles, we fucked')
            elif game.home_team.location == 'los angeles':
                team = game.home_team
            elif game.away_team.location == 'los angeles':
                team = game.away_team
            else:
                print team_identifier
                raise Exception('too many teams but not all la, wtf')
    return team

def process_play(**params):
    function = 'process_%s(**params)' % params['event_type']
    eval(function)

def process_timeout(**params):
    req = ['session', 'league', 'play_info']
    opt = ['team']
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    timeout = re.compile(
              r"(?P<team_identifier>\b.+?\b)? ?"
              "(?P<timeout_type>full|20 sec.|official)? ?"
              "(?:timeout)"
              "(?: called by )?"
              "(?P<player_name>.+)?")
    match = timeout.match(event)
    action = 'timeout'
    if match:
        team_identifier, timeout_type, player_name = match.groups()
        if team_identifier: 
            if team_identifier in ['official', '20. sec.', 'full']:
                team_id = None
                timeout_type = team_identifier
            else:
                team_identifier = team_identifier.strip()                 
                team = get_team(game, session, league, 
                                team_identifier, event)
                if not team == params['team']:
                    raise Exception('team mismatch')
                team_id = team.id
        else:
            team_id = None
        if timeout_type:
            timeout_type = timeout_type.replace('sec.', 'second').lower()
        if player_name:
            player = get_player(session, league.id, 
                                play_info['full_description'], 
                                player_name, team)
            timeout, created = get_or_create(session, PlayerTimeout, 
                                             team_id=team_id, 
                                             timeout_type=timeout_type,
                                             action=action, 
                                             player_id=player.id, 
                                             **play_info)
        else:
            timeout, created = get_or_create(session, Timeout, 
                                             team_id=team_id, 
                                             timeout_type=timeout_type, 
                                             action=action,
                                             **play_info)    
    else:
        print event
        raise Exception('unknown timeout')
    return timeout
    
def process_clock(**params):
    req = ['session', 'play_info']
    opt = []
    session, play_info = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    if 'start' in event:
        action = 'start of period'
    elif 'end of the' in event:
        action = 'end of period'
    elif 'end game' in event:
        action = 'end of game'
    else:
        print event
        raise Exception('unknown clock event')
    clock, created = get_or_create(session, Clock,
                                   action=action, 
                                   **play_info)
    return clock
   
def process_substitution(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    substitution = re.compile(
                   "(?P<enters>.+?)? ?"
                   "enters the game for ? ?"
                   "(?P<leaves>.+)?")
    match = substitution.match(event)
    if match:
        player_in, player_out = match.groups()
        if player_in and player_out:
            player_in, player_out = [get_player(session, league.id, 
                                                play_info['full_description'],
                                                player_name, team) 
                                     for player_name in [player_in, 
                                                         player_out]]
            if not player_in or not player_out:
                print event
            substition, created = get_or_create(session, Substitution,
                                                team_id=team.id,
                                                player_in_id=player_in.id, 
                                                player_out_id=player_out.id, 
                                                **play_info)
        elif player_out:
            player_out = get_player(session, league.id,
                                    play_info['full_description'],
                                    player_out, team)
            substition, created = get_or_create(session, Substitution,
                                                team_id=team.id, 
                                                player_out_id=player_out.id, 
                                                **play_info)
        elif player_in:
            player_in = get_player(session, league.id, 
                                   play_info['full_description'], 
                                   player_in, team)
            substition, created = get_or_create(session, Substitution,
                                                team_id=team.id, 
                                                player_in_id=player_in.id, 
                                                **play_info)
        return substitution
    else:
        print event
        raise Exception('unknown substitution')
        
def process_jumpball(**params):
    req = ['session', 'league', 'play_info', 'team', 
           'other_team', 'game', 'home']
    opt = []
    (session, league, play_info, 
     team, other_team, game, home) = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    jumpball = re.compile(
               "(?:jumpball\: )? ?"
               "(?P<player_a>.+) vs\.  ?(?P<player_b>.+) "
               "\((?P<possesor>.+) "
               "gains possession\)")
    match = jumpball.match(event)
    if match:
        player_a, player_b, possessor_name = match.groups()
        if home is True:
            winner, loser = player_b, player_a
        else:
            winner, loser = player_a, player_b
        winner = get_player(session, league.id, 
                            play_info['full_description'], 
                            winner, team)
        loser = get_player(session, league.id, 
                           play_info['full_description'], 
                           loser, other_team)
        if not winner or not loser:
            print event
            print player_a
            print player_b
            raise Exception('jumpball players not found')
        try:
            possessor = get_player(session, league.id, 
                                   play_info['full_description'], 
                                   possessor_name, team)
            if not possessor:
                possession_team = get_team(game, session, league, 
                                           possessor_name)
                if possession_team == team:
                    jumpball, created = get_or_create(session, Jumpball, 
                                              winner_id=winner.id, 
                                              loser_id=loser.id,
                                              possession_team_id=team.id,
                                              **play_info)
                else:
                    print event
                    print possessor_name
                    print possession_team
                    print team
                    raise Exception('jumpball team mismatch')
            else:
                jumpball, created = get_or_create(session, PlayerJumpball, 
                                              winner_id=winner.id, 
                                              loser_id=loser.id, 
                                              possessor_id=possessor.id,
                                              possession_team_id=team.id, 
                                              **play_info)
        except NoResultFound:
            team_identifier = possessor.lower()
            possession_team = get_team(game, session, league, team_identifier)
            if not possession_team == team:
                print possession_team
                print team
                raise Exception('unmatched teams')
            else:
                jumpball, created = get_or_create(session, Jumpball, 
                                              winner_id=winner.id,
                                              loser_id=loser.id,
                                              possession_team_id=team.id, 
                                              **play_info)
        return jumpball
    else:
        print event
        raise Exception('unknown jumpball event')
        
def process_steal(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team', 'game']
    opt = []
    (session, league, play_info, 
     team, other_team, game) = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    steal = re.compile(
            "(?P<turnerover_name>.+?) "
            "(?P<steal_type>bad pass|jump ball violation|"
            "lost ball|out of bounds lost ball|post lost ball)? ?"
            "(?:turnover )?"
            "\( ?(?P<stealer_name>.+) "
            "steals\)")
    match = steal.match(event)
    if match:
        turnover_name, steal_type, stealer_name = match.groups()
        result = 'turnover'
        turnerover = get_player(session, league.id, 
                                play_info['full_description'], 
                                turnover_name, team)
        stealer = get_player(session, league.id, 
                             play_info['full_description'],
                             stealer_name, other_team)
        if not turnerover or not stealer:
            pprint(turnover_name)
            pprint(stealer_name)
            print event
            raise Exception('steal players not found')
        steal, created = get_or_create(session, Steal, 
                                       stealer_id=stealer.id, 
                                       turnerover_id=turnerover.id, 
                                       steal_type=steal_type, 
                                       result=result, 
                                       team_id=team.id, 
                                       **play_info)
        return steal
    else:
        print pprint(event)
        raise Exception('unknown steal')
    
def process_team_foul(**params):
    req = ['session', 'play_info', 'team']
    opt = []
    session, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    foul_type = 'technical'
    if 'delay' in event:
        description = 'delay of game'
    elif 'timeout' in event:
        description = 'excess timeout'
    elif event == 'technical foul':
        description = None
    foul, created = get_or_create(session, Foul, 
                                  foul_type=foul_type, 
                                  description=description, 
                                  team_id=team.id, 
                                  **play_info)
    return foul

def process_draw_foul(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team', 'game']
    opt = []
    (session, league, play_info, 
     team, other_team, game) = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    event = event.replace('offensiveCharge', 'offensive charge')\
                 .replace('flagrantfoultype1', 'flagrant foul type 1')
    draw_foul = re.compile(
                "(?P<commits>.+?) "
                "(?P<foul_description>hanging on rim|"
                     "loose ball|shooting|inbound|clear path|"
                     "offensive|block|take|charge|flagrant|"
                     "away from ball|punching)? ?"
                "(?:personal)? ?"
                "(?:foul)? ? ?"
                "(?:type (?P<flagrant_type>[1,2]))? ?"
                "(?:take|charge|block|charging)? ?"
                "(?:foul)? ?"
                "\( ?(?P<draws>.+) draws the foul ?\)")
    match = draw_foul.match(event)
    if match:
        commits_name, description, flagrant_type, draws_name = match.groups()
        foul_type = 'personal'        
        if description == 'charge':
            description = 'offensive'
        if flagrant_type:
            description = '%s %s' % (description, flagrant_type)
        commiter = get_player(session, league.id, 
                              play_info['full_description'], 
                              commits_name, team)
        drawer = get_player(session, league.id, 
                            play_info['full_description'], 
                            draws_name, other_team)
        if not commiter or not drawer:
            pprint(commits_name)
            pprint(draws_name)
            print event
            raise Exception('foul people not found')
        foul, created = get_or_create(session, DrawFoul, 
                                      commiter_id=commiter.id, 
                                      drawer_id=drawer.id, 
                                      foul_type=foul_type,
                                      description=description,
                                      team_id=team.id, 
                                      **play_info)
        return foul
    else:
        print event  
        raise Exception('unknown draw foul') 

def process_double_foul(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team']
    opt = []
    (session, league, play_info, team, other_team) = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    description = 'double'    
    double_foul = re.compile(
                  "double "
                  "(?P<foul_type>personal|technical) "
                  "foul: "
                  "(?P<player_a>.+?) "
                  "(?:\([0-9]\) )?"
                  "and "
                  "(?P<player_b>[A-Z,a-z,\.,\',\s]+(?!\([0-9]\)))"
                  "(?:.+)?")
    match = double_foul.match(event)
    if match:
        foul_type, player_a, player_b = match.groups()
        for player_name, player_team in [(player_a, team), 
                                         (player_b, other_team)]:
            commiter = get_player(session, league.id,
                                  play_info['full_description'],
                                  player_name, player_team)
            if not commiter:
                pprint(player_name)
                print event
                raise Exception('player not found for double found')
            foul, created = get_or_create(session, PlayerFoul,
                                          team_id=player_team.id,
                                          commiter_id=commiter.id, 
                                          foul_type=foul_type, 
                                          description=description, 
                                          **play_info)
    else:
        double_foul = re.compile(
                      "(?P<player_name>.+) "
                      "double "
                      "(?P<foul_type>personal|technical) "
                      "foul")
        match = double_foul.match(event)
        if match:
            player_name, foul_type = match.groups()
            commiter = get_player(session, league.id, 
                                  play_info['full_description'],
                                  player_name, team)
            foul, created = get_or_create(session, PlayerFoul, 
                                          team_id=team.id,
                                          commiter_id=commiter.id, 
                                          foul_type=foul_type, 
                                          description=description, 
                                          **play_info)
        else:
            print event
            raise Exception('unknown double foul')
    return foul

def process_illegal_defense(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    violation_type = 'illegal defense'
    result = 'free throw'    
    illegal_defense = re.compile(
                      "(?P<violator_name>.+) "
                      "(?:illegal defense|defensive 3-seconds)"
                      "(?: foul| \(Technical Foul\))?")
    match = illegal_defense.match(event)
    if match:
        violator_name = match.groupdict()['violator_name']
        violator = get_player(session, league.id, 
                              play_info['full_description'],
                              violator_name, team)
        if not violator:
            team_identifier = violator_name.rpartition(' ')[2]
            violator_team = get_team(game, session, league, team_identifier)
            if violator_team == team:                
                violation, created = get_or_create(session, Violation,
                                           team_id=team.id, 
                                           violation_type=violation_type,
                                           result=result,
                                           **play_info)
            else:
                print event
                print violator_name
                raise Exception('unknown violator')
        else:
            violation, created = get_or_create(session, PlayerViolation,
                                               team_id=team.id,
                                               violator_id=violator.id, 
                                               violation_type=violation_type,
                                               result=result,
                                               **play_info)
    elif event == 'illegal defense foul':
        violation, created = get_or_create(session, Violation,
                                           team_id=team.id, 
                                           violation_type=violation_type,
                                           result=result,
                                           **play_info)
    else:
        print event
        raise Exception('unknown illegal defense')
    return violation

def process_off_turnover(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    off_turnover = re.compile(
                    "(?P<player_name>.+) "
                    "(?:off|offensive) "
                    "foul"
                    "(?: turnover)?")
    match = off_turnover.match(event)
    foul_type = 'personal'
    description = 'offensive'
    if match:
        player_name = match.groupdict()['player_name']
        commiter = get_player(session, league.id, 
                              play_info['full_description'],
                              player_name, team)
        foul, created = get_or_create(session, PlayerFoul,
                                      team_id=team.id, 
                                      commiter_id=commiter.id, 
                                      foul_type=foul_type, 
                                      description=description, 
                                      **play_info)
    else:
        print event
        raise Exception('unknown off foul turnover')
    return foul

def process_num_foul(**params):
    req = ['session', 'league', 'play_info', 'team', 'game']
    opt = []
    session, league, play_info, team, game = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    num_foul = re.compile(
               "(?P<commits>.+?) "
               "(?:team )?"
               "(?P<foul_extra>taunting|non-unsportsmanlike)? ?"
               "(?P<foul_description>loose ball|offensive|technical|"
                        "hanging on rim|shooting|personal|foul|inbound) "
               "(?:foul)? ?"
               "(?:\([0-9]{0,2}[a-z]{2} "
               "(?P<foul_type>personal|technical) "
               "foul\))?")
    match = num_foul.match(event)
    if match:
        commits_name, foul_extra, description, foul_type = match.groups()
        if description == 'technical' and foul_type == 'personal':
            foul_type = 'technical'
        if foul_extra:
            description = foul_extra
        if description in ('technical', 'personal', 'foul'):
            description = None
        commiter = get_player(session, league.id, 
                              play_info['full_description'],
                              commits_name, team)
        if not commiter:
            try:
                commits_name = commits_name.title()
                coach = session.query(Coach)\
                               .join(TeamCoach)\
                               .filter(TeamCoach.team_id==team.id)\
                               .join(Person).join(PersonName)\
                               .filter(PersonName.full_name==commits_name)\
                               .one()
                foul, created = get_or_create(session, CoachFoul,
                                              team_id=team.id, 
                                              commiter_id=coach.id, 
                                              foul_type=foul_type, 
                                              description=description, 
                                              **play_info)
            except NoResultFound:
                team = get_team(game, session, league, commits_name.lower())
                if team:                    
                    foul, created = get_or_create(session, Foul,
                                                  team_id=team.id, 
                                                  foul_type=foul_type, 
                                                  description=description, 
                                                  **play_info)
                else:
                    pprint(commits_name)
                    print team
                    print event
                    raise Exception('no coach')
        else:
            foul, created = get_or_create(session, PlayerFoul,
                                          team_id=team.id, 
                                          commiter_id=commiter.id, 
                                          foul_type=foul_type, 
                                          description=description, 
                                          **play_info)
    elif event == 'technical foul' or 'team technical' in event:
        foul_type = 'technical'
        description = None     
        foul, created = get_or_create(session, Foul, 
                                      foul_type=foul_type, 
                                      description=description, 
                                      team_id=team.id, 
                                      **play_info)
    else:
        num_foul = re.compile(
                   "(?P<commits>.+?) "
                   "(?:foul )?\([0-9]{0,2}[a-z]{2} "
                   "(?P<foul_type>personal|technical) "
                   "foul\)")
        match = num_foul.match(event)
        if match:
            commits_name, foul_type = match.groups()
            description = None
            commiter = get_player(session, league.id, 
                                  play_info['full_description'], 
                                  commits_name, team)
            foul, created = get_or_create(session, PlayerFoul,
                                          team_id=team.id,
                                          commiter_id=commiter.id, 
                                          foul_type=foul_type, 
                                          description=description, 
                                          **play_info)
        else:
            print event
            raise Exception('unknown num foul')
    return foul

def process_special_turnover(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    result = 'turnover'
    if event == 'shot clock turnover':
        violation_type = 'shot clock'
    elif event == 'turnover':
        violation_type = None
    elif event == 'bad pass':
        violation_type = 'bad pass'
    elif event == '5 sec inbound turnover':
        violation_type = '5 second'
    violation, created = get_or_create(session, Violation,
                                       team_id=team.id, 
                                       violation_type=violation_type,
                                       result=result,
                                       **play_info)
    return violation

def process_turnover(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team']
    opt = []
    session, league, play_info, team, other_team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    turnover = re.compile(
           "(?P<player_name>.+?) "
           "(?P<violation_type>double personal|palming|"
               "out of bounds lost ball|step out of bounds|"
               "post lost ball|illegal screen|illegal assist|"
               "basket from elbows|steps out of bounds|bad pass|"
               "opposite basket|swinging elbows|punched ball)? ?"
           "turnover")
    match = turnover.match(event)
    if match:
        player_name, violation_type = match.groups()
        player = get_player(session, league.id, 
                            play_info['full_description'], 
                            player_name, team)
        if player_name == 'team':
            result = 'turnover'        
            violation, created = get_or_create(session, Violation,
                                               team_id=team.id,
                                               violation_type=violation_type,
                                               result=result, 
                                               **play_info)
        elif not player:
            team_identifier = player_name.rpartition(' ')[2].lower()
            violation_team = get_team(game, session, league, team_identifier,
                                      play_info['full_description'])
            if violation_team == team:
                result = 'turnover'
                violation, created = get_or_create(session, Violation,
                                               team_id=team.id,
                                               violation_type=violation_type,
                                               result=result, **play_info)
                return violation
            else:
                print event
                print player_name
                raise Exception('unknown player for turnover')
        elif violation_type in ['illegal screen', 'double personal', 
                                'swinging elbows']:
            foul_type = 'personal'
            if violation_type == 'illegal screen':
                description = 'illegal screen'
            elif violation_type == 'double personal':
                description = 'double'
            elif violation_type == 'swinging elbows':
                description = 'swinging elbows'
            foul, created = get_or_create(session, PlayerFoul, 
                                          team_id=team.id,
                                          commiter_id=player.id, 
                                          foul_type=foul_type, 
                                          description=description, 
                                          **play_info)
            return foul
        else:
            result = 'turnover'
            violation, created = get_or_create(session, PlayerViolation,
                                               team_id=team.id,
                                               violator_id=player.id,
                                               violation_type=violation_type,
                                               result=result, **play_info)
            return violation
    else:
        print event
        raise Exception('unknown turnover')

def process_free_throw(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    shot_type = 'free throw'
    points = 1
    free_throw = re.compile(
                 '(?P<shooter_name>.+) (?P<makes>misses|makes) '
                 '(?P<adjective>technical|flagrant|)? ?free throw '
                 '?(?:[1-3] of [1-3])?')
    match = free_throw.match(event)
    if match:
        shooter_name, makes, adjective = match.groups()
        make = True if makes == 'makes' else False
        shooter = get_player(session, league.id, 
                             play_info['full_description'], 
                             shooter_name, team)
        free_throw, created = get_or_create(session, Shot, 
                                            shooter_id=shooter.id,
                                            shot_type=shot_type,
                                            make = make,
                                            points=points, 
                                            **play_info)
    else:
        print event
        raise Exception('unknown free throw')
    return free_throw
        
def process_shot(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team']
    opt = []
    session, league, play_info, team, other_team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    shot = re.compile(
               "(?P<shooter_name>.+) "
               "(?P<result>makes|misses) ?"
               "(?:(?P<length>[0-9]{1,2})-foot)? ?"
               "(?P<adjective>.+?)? "
               "(?P<shot_type>shot|jumper|dunk|layup|pointer) ?"
               "(?:\( ?(?P<assistant_name>.+?) assists\))?")   
    match = shot.match(event)
    if match:
        (shooter_name, result, length, 
         adjective, shot_type, assistant_name) = match.groups()
    if not match:
        shot = re.compile(
               "(?P<shooter_name>.+) "
               "(?P<result>makes|misses) ?"
               "(?:(?P<length>[0-9]{1,2})- foot)?")
        match = shot.match(event)
        if match:
            shooter_name, result, length = match.groups()
            adjective = None
            shot_type = None
            assistant_name = None
    if match:
        shooter = get_player(session, league.id, 
                             play_info['full_description'], 
                             shooter_name, team)
        if adjective:
            adjective = adjective.lower()
        if shot_type:
            shot_type = shot_type.lower()
        if adjective in ('tip', 'hook'):
            shot_type = adjective
            adjective = None
        points = 2
        if adjective:
            if 'three' in adjective:
                points = 3
                if adjective == 'three point hook':
                    shot_type = 'hook'
                    adjective = ''
                adjective = adjective.replace('three', '')\
                                     .replace('pointer', '')\
                                     .replace('point', '')\
                                     .strip()
                if adjective == '':
                    adjective = None
        if shot_type == 'pointer':
            shot_type = 'jumper'
        make = True if result == 'makes' else False 
        if assistant_name:
            assistant = get_player(session, league.id, 
                                   play_info['full_description'], 
                                   assistant_name, team)
            if not assistant:
                pprint(assistant_name)
                pprint(event)
                raise Exception('unknown assistant')
            assisted_shot, created = get_or_create(session, Assist, 
                                                   team_id=team.id, 
                                                   shooter_id=shooter.id, 
                                                   length=length, 
                                                   shot_type=shot_type, 
                                                   make=make, 
                                                   adjective=adjective, 
                                                   assistant_id=assistant.id,
                                                   points=points, 
                                                   **play_info)
        else:
            shot, created = get_or_create(session, Shot, 
                                          team_id=team.id, 
                                          shooter_id=shooter.id, 
                                          length=length, 
                                          shot_type=shot_type, 
                                          make=make, adjective=adjective,
                                          points=points, 
                                          **play_info)
    else:
        if event == 'misses':
            make = False            
            shot, created = get_or_create(session, Shot, 
                                          team_id=team.id, 
                                          make=make, 
                                          **play_info)
        else:
            pprint(event)
            raise Exception('unknown shot')
    return shot

def process_block(**params):
    req = ['session', 'league', 'play_info', 'team', 'other_team']
    opt = []
    session, league, play_info, team, other_team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    block = re.compile(
            "(?P<blocker_name>.+) blocks "
            "(?P<shooter_name>.+)'s "
            "(?:(?P<length>[0-9]+)-foot)? "
            "?(?P<adjective>.+)? "
            "?(?P<shot_type>shot|jumper|dunk|layup|three pointer)")
    match = block.match(event)
    if match:
        make = False
        (blocker_name, shooter_name, 
         length, adjective, shot_type) = match.groups()
        if adjective:
            adjective = adjective.strip()
        if adjective in ('tip', 'hook'):
            shot_type = adjective
            adjective = None                        
        points = 2
        if adjective == 'three point':
            points = 3
        if shot_type == 'three pointer':
            points = 3
            shot_type = 'jumper'
            adjective = None
        shooter = get_player(session, league.id, 
                             play_info['full_description'], 
                             shooter_name.strip(), team)
        blocker = get_player(session, league.id, 
                             play_info['full_description'], 
                             blocker_name.strip(), other_team)
        if not shooter or not blocker:
            pprint(blocker_name)
            pprint(shooter_name)
            print event
            raise Exception('players in blocked shot not found')
        blocked_shot, created = get_or_create(session, Block, 
                                              team_id=team.id, 
                                              shooter_id=shooter.id, 
                                              length=length, 
                                              shot_type=shot_type, 
                                              make=make, 
                                              adjective=adjective,
                                              blocker_id=blocker.id,
                                              points=points, 
                                              **play_info)
    else:
        print event
        raise Exception('unknown block')
    return block

def process_rebound(**params):
    req = ['session', 'league', 'play_info', 'team', 'game']
    opt = []
    session, league, play_info, team, game = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    event = event.strip()
    rebound = re.compile(
              '(?P<rebounder_name>.+?)? ?'
              '(?P<offensive>offensive|defensive) ?'
              '(?P<is_team>team)? ?'
              'rebound')
    match = rebound.match(event)
    if match:
        rebounder_name, offensive, is_team = match.groups()
        if offensive == 'offensive':
            offensive = True
        else:
            offensive = False
        if is_team or not rebounder_name:
            if rebounder_name and (not rebounder_name 
                                   in team.all_names()):
                pprint(event)
                pprint(team)
                pprint(rebounder_name)
                print (rebounder_name in team.all_names())
                print team.all_names()
                raise Exception('team rebound city mismatch')
            rebound, created = get_or_create(session, Rebound, 
                                             team_id=team.id, 
                                             offensive=offensive, 
                                             **play_info)
        else:
            if rebounder_name in team.all_names():
                rebound, created = get_or_create(session, Rebound, 
                                             team_id=team.id, 
                                             offensive=offensive, 
                                             **play_info)
            else:
                player = get_player(session, league.id, 
                                    play_info['full_description'], 
                                    rebounder_name, team)
                if player:
                    rebound, created = get_or_create(session, PlayerRebound,
                                                     rebounder_id=player.id,
                                                     team_id=team.id, 
                                                     offensive=offensive, 
                                                     **play_info)
                else:
                    team = get_team(game, session, league, rebounder_name)
                    rebound, created = get_or_create(session, Rebound,
                                                     rebounder_id=player.id,
                                                     team_id=team.id, 
                                                     offensive=offensive, 
                                                     **play_info)
    else:
        print event
        raise Exception('unknown rebound')
    return rebound

def process_ejection(**params):
    req = ['session', 'league', 'play_info', 'team']
    opt = []
    session, league, play_info, team = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    ejection = '(?P<player_name>.+) ejected'
    match = re.match(ejection, event)
    if match:
        player_name = match.groupdict()['player_name']
        player = get_player(session, league.id, 
                            play_info['full_description'],
                            player_name, team)
        ejection, created = get_or_create(session, Ejection, 
                                          player_id=player.id, 
                                          team_id=team.id, 
                                          **play_info)
    else:
        print event 
        raise Exception('unknown ejection')

def process_violation(**params):
    req = ['session', 'league', 'play_info', 'team', 'game']
    opt = []
    session, league, play_info, team, game = get_many(params, req, opt)
    event = play_info['full_description'].lower()
    violation = re.compile(
                "(?P<player_name>.+?)? ?"
                "(?:(?:Turnover|Violation) ?: ?)?"
                "(?P<violation_type>kicked ball|bad pass|traveling|"
                    "backcourt|defensive goaltending|lane|3 second|"
                    "discontinue dribble|double dribble|"
                    "offensive goaltending|delay of game|jump ball|"
                    "inbound|lost ball|10 second|5 second|8 second|"
                    "out of bounds|shot clock|illegal defense|"
                    "travelling|violation|kick ball) ?"
                "(?:violation)?")
    match = violation.match(event)
    if match:
        player_name, violation_type = match.groups()
        if violation_type == 'violaton':
            violation_type = None
        elif violation_type == 'travelling':
            violation_type = 'traveling'
        if player_name in ['delay of game', 'shot clock']:
            violation_type = player_name
            player_name = None
        if violation_type == 'defensive goaltending':
            result = 'points'
        elif violation_type == 'lane':
            result = None
        elif violation_type == 'delay of game':
            result = None
        else:
            result = 'turnover'
        if player_name:
            player = get_player(session, league.id, 
                                play_info['full_description'], 
                                player_name, team)
            if not player:
                team_identifier = player_name.lower()
                violation_team = get_team(game, session, league, 
                                          team_identifier)
                if team == violation_team:
                    violation, created = get_or_create(session, Violation,
                                               team_id=team.id,
                                               violation_type=violation_type,
                                               result=result,
                                               **play_info)
                else:
                    print team
                    print violation_team
                    print event
                    raise Exception('violation team not good')
            else:
                violation, created = get_or_create(session, PlayerViolation,
                                               team_id=team.id,
                                               violator_id=player.id,
                                               violation_type=violation_type,
                                               result=result,
                                               **play_info)
        else:
            violation, created = get_or_create(session, Violation,
                                               team_id=team.id,
                                               violation_type=violation_type,
                                               result=result,
                                               **play_info)
    else:
        player = get_player(session, league.id, 
                            play_info['full_description'], 
                            event, team)
        if not player:
            if not event in ['misses']:
                print event
                raise Exception('unknown event')
    return violation
