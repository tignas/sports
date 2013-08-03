# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
import feedparser
import urllib, urllib2
import re
from pprint import pprint
from BeautifulSoup import BeautifulSoup
from datetime import datetime
from time import mktime
from dateutil import parser
from connect_db import *
from sqlalchemy import and_, or_, desc, func
from bizarro.models.play_by_play import *
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.media import *
from bizarro.models.fantasy import *
from itertools import groupby
from sqlalchemy.orm import aliased, eagerload, joinedload, subqueryload
from sqlalchemy.sql import exists
from bizarro.api.sums import *
from apex.models import *
from apex.lib.libapex import create_user
session = create_session(True)
engine = this_engine()

def delete(obj):
    session.delete(obj)
    session.commit()    
def save(obj):
    session.add(obj)
    session.commit()

a = session.query(FootballPuntingStat.id, func.sum(FootballPuntingStat.total)).join(Game, Season).filter(Game.game_type=='reg', Season.year==2012, Game.league_id==1).first()

print a

'''
a = session.query(PlayerExternalID).join(Player).filter(Player.league_id==1)
print a.count()
base_url = 'http://espn.go.com/nfl/player/_/id/%s/'

for num, b in enumerate(a):
    url = base_url % b.external_id
    res = urllib2.urlopen(url)
    body = BeautifulSoup(res)
    bday = body.find('span', text='Born').findPrevious('li').text
    bday = bday.split('Born')[1].split(' in')[0]
    bday = parser.parse(bday)
'''











