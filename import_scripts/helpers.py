from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import or_
from pprint import pprint
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from connect_db import *

def get_team(session, league, team_identifier, full_description=None):
    #Try team_abbr
    try:
        team = session.query(Team).filter(or_(Team.abbr==team_identifier, 
                                              Team.name==team_identifier,
                                              Team.location==team_identifier))\
                      .join(LeagueTeam).filter(LeagueTeam.league_id==league.id)\
                      .one()
    except NoResultFound:
        try:
            team = session.query(Team)\
                          .join(TeamName, LeagueTeam)\
                          .filter(LeagueTeam.league_id==league.id,
                                  TeamName.abbr==team_identifier)
            team = team.one()
        except NoResultFound:
            print full_description
            print 'no team found for %s' % team_identifier
            raise Exception('no teams')
        except MultipleResultsFound:
            print full_description
            print team_identifier
            print team.all()
            raise Exception('too many teams')
    except MultipleResultsFound:
        print team_identifier
    return team
    
def get_player(session, league_id, full_name, team=None):
    try:
        players = session.query(Player).filter(Player.league_id==league_id)\
                        .join(Person).join(PersonName)\
                        .filter(PersonName.full_name==full_name)
        player = players.one()
        return player
    except NoResultFound:
        return None
    except MultipleResultsFound:
        if team:
            players = session.query(Player).filter(Player.league_id==league_id)\
                        .join(TeamPlayer).filter(TeamPlayer.team_id==team.id)\
                        .join(Person).join(PersonName)\
                        .filter(PersonName.full_name==full_name)
            player = players.one()
            return player
        else:
            print players.all()
            raise Exception('too many players yo')
    
def get_or_create_player(session, league_id, full_name):
    player = get_player(session, league_id, full_name)
    if not player:
        player = create_player(session, league_id, full_name)
    return player

def create_player(session, league_id, full_name=None):
    person = Person()
    person = save(session, person)
    player = Player(person_id=person.id, league_id=league_id) 
    player = save(session, player)
    if full_name:        
        name = PersonName(full_name=full_name, person_id=person.id)
        name = save(session, name)
    return player
    

def create_full_player(session, full_name, external_id, height, weight, 
                        college, league, team, source, position_abbr, 
                        number, sport):
    player_external_id, created = get_or_create(session, PlayerExternalID, 
                                                source_name=source.name,
                                                league_id=league.id,
                                                external_id=external_id)
    player = player_external_id.player
    if not player:
        person = Person()       
        person = save(session, person)
        player = Player(person_id=person.id, league_id=league.id)
        player = save(session, player)
        player_external_id.player = player
        save(session, player_external_id)
    else:
        person = player.person
    name, created = get_or_create(session, PersonName, full_name=full_name, 
                                  person_id=person.id)
    try:
        position = session.query(Position).filter_by(abbr=position_abbr, 
                                                 sport_name=sport).one()
    except NoResultFound:
        pprint(position_abbr)
        raise Exception('no position found')
    if not position in player.positions:
        player.positions.append(position)
        save(session, player)
    '''
    team_player, created = get_or_create(session, TeamPlayer, team_id=team.id, 
                                         player_id=player.id)
    '''
    team_players = session.query(TeamPlayer)\
                          .filter(TeamPlayer.player==player, 
                                  TeamPlayer.team==team)\
                          .all()
    if team_players:
        for num, p in enumerate(team_players):
            if not num == 0:
                session.delete(team_players[num])
        team_players[0].current=True
    else:
        team_player = TeamPlayer(team=team, player=player, current=True)
    session.commit()
    height_weight, created = get_or_create(session, HeightWeight, 
                                           person_id=person.id)
    if height > 0 and not height_weight.height:
        height_weight.height = height
        save(session, height_weight)
    if weight > 0 and not height_weight.weight:
        height_weight.weight = weight
        save(session, height_weight)
    if college:
        college, created = get_or_create(session, College, name=college)
        person_college = get_or_create(session, CollegePerson, 
                                       person_id=person.id, 
                                       college_name=college.name)
    if not number == '--':
        number = int(number)
        team_player_number = get_or_create(session, PlayerNumber, 
                                           player_id=player.id, number=number)
    return player
        
    
