# -*- coding: utf-8 -*-

from connect_db import *
from sqlalchemy import and_, or_, desc, func
from bizarro.models.play_by_play import *
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.media import *
from bizarro.models.fantasy import *
from itertools import groupby, ifilter, ifilterfalse
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
    
