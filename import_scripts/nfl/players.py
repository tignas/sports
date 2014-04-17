import datetime
import urllib, urllib2
from BeautifulSoup import BeautifulSoup
from sqlalchemy.orm.exc import NoResultFound
from connect_db import create_session, get_or_create
from bizarro.models.teams import *
from bizarro.models.people import *
from ..helpers import create_full_player
                                           
def import_roster(league, teams):
    session = create_session()
    source_name = 'espn'
    source, created = get_or_create(session, Source, name=source_name)
    sport = 'football'
    for team in teams:
        print team.abbr
        url = 'http://espn.go.com/nfl/team/roster/_/name/%s/'
        url %= team.abbr
        result = urllib2.urlopen(url)
        body = BeautifulSoup(result)
        player_search = r'evenrow|oddrow player'
        players= body.findAll('tr', 
                              attrs={'class':re.compile(player_search)})
        if not players:
            raise Exception('no players for this team')
        for player_row in players: 
            info = player_row.findAll('td')
            number = info[0].text              
            full_name = info[1].text           
            external_id = info[1].a['href'].partition('id/')[2].\
                                        partition('/')[0]
            position = info[2].text.lower()
            height = info[4].text.partition('-')
            try:
                feet = int(height[0])
                inches = int(height[2])                    
                height = feet*12 + inches
            except ValueError:
                height = None
            try:
                weight = int(info[5].text)
            except ValueError:
                weight = None
            college = info[7].text.replace(';', '').strip()
            player = create_full_player(session, full_name, external_id, height, 
                                   weight, college, league, team, source, 
                                   position, number, sport)
