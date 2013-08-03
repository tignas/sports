import json
from itertools import groupby
from pyramid.view import view_config
from sqlalchemy.orm import aliased, eagerload
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import and_, or_, desc, func
from bizarro.models.people import *
from bizarro.models.media import Writer, Source
from connect_db import create_session

def get_or_create_writer(session, writer_name, source):
    try:
        writer = session.query(Writer)\
                        .join(Person, PersonName)\
                        .filter(PersonName.full_name==writer_name)\
                        .one()
    except NoResultFound:
        writer = Writer(person=Person())
        session.add(writer)
        session.commit()
        writer.person.names.append(PersonName(full_name=writer_name))
        writer.sources.append(source)
        session.commit()
    return writer
                
