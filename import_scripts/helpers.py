from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import or_
from connect_db import *
from pprint import pprint

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
        
    
