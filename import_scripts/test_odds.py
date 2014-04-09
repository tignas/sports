import json
import datetime
import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import re
from pprint import pprint
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

def import_game(league_abbr, game_id):
    if league_abbr == 'nba':
        urls = {
            'consensus': 'http://contests.covers.com/Handicapping/ConsensusPick/consensus-pick.aspx?sport=nba&sportID=9&eventID=%d'
        }
        for cat, url in urls.iteritems():
            url %= game_id
            result = urllib2.urlopen(url)
            body = BeautifulSoup(result)
            avg = body.find('td', text='VS.').findPrevious('tr').findAll('td')
            away = avg[1].text[:-1]
            home = avg[3].text[:-1]
            items = body.find('td', text='Visitor')\
                        .findPrevious('table')\
                        .findAll('tr')
            for item in items[1:-1]:
                line = item.findAll('td')[1:5]
                line = line
                
            
            
import_game('nba', 740644) 
