from helpers import get_team, create_player, get_player, get_or_create_player
import json
import datetime
import urllib, urllib2
from BeautifulSoup import BeautifulSoup
from bizarro.connect_db import *
import re
from pprint import pprint
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.meta import *
from pprint import pprint
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

def import_odds(league_abbr):
    #league = session.query(League).filter(League.abbr==league_abbr).one()
    if league_abbr == 'nba':
        session = create_session()
        source_name = 'covers'
        '''
        url = 'http://www.covers.com/pageLoader/pageLoader.aspx?page=/data/nba/teams/teams.html'
        result = urllib2.urlopen(url)
        body = BeautifulSoup(result)
        team_links = body.find('h1').findNext('table').findAll('a')
        for team_link in team_links:
            team_name = team_link.text.lower()
            covers_id = team_link['href'].rpartition('/')[2]\
                                         .partition('m')[2]\
                                         .partition('.')[0]
            if 'l.a.' in team_name:
                team_name = team_name.rpartition('. ')[2]
                team = session.query(Team)\
                              .join(LeagueTeam, League)\
                              .filter(League.abbr==league_abbr,
                                      Team.name==team_name)\
                              .one()
            else:
                team = session.query(Team)\
                              .join(LeagueTeam, League)\
                              .filter(League.abbr==league_abbr,
                                      Team.location==team_name)\
                              .one()
            team_external_id, created = get_or_create(session, TeamExternalID,
                                                      external_id=covers_id,
                                                      source_name=source_name,
                                                      team_id=team.id)
        '''
        '''
        teams = session.query(TeamExternalID)\
                       .join(Team, LeagueTeam, League)\
                       .filter(League.abbr==league_abbr,
                               TeamExternalID.source_name==source_name)\
                       .all()
        base_url = 'http://www.covers.com/pageLoader/pageLoader.aspx?page=/data/nba/teams/pastresults/%d-%d/team%s.html'
        seasons = range(2003, 2013)
        for team in teams:
            print team
            for season in seasons:
                print season
                url = base_url
                url %= (season, season+1, team.external_id)
                result = urllib2.urlopen(url)
                body = BeautifulSoup(result)
                links = body.findAll('a', href=re.compile('\/pageLoader\/pageLoader.aspx\?page\=\/data\/nba\/results\/'))
                for link in links:
                    game_id = link['href'].partition('score')[2]\
                                          .partition('.')[0]
                    external_game_id = get_or_create(session, GameExternalID,
                                                     external_id=game_id,
                                                     source_name=source_name)
                                      
        '''
                                      
                                      
                                      
                                      
                                      
                
