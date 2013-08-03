from meta import *
from media import Source
from teams import Team
from stats import ExternalID
from sqlalchemy import select, func, and_, Unicode
from apex.models import AuthID

'''
class Users(Base):

    id = Column(Integer, primary_key=True)
    auth_id = Column(Integer, ForeignKey(AuthID.id), index=True)
    first_name = Column(Unicode(80))
    last_name = Column(Unicode(80))

    user = relationship(AuthID, backref=backref('profile', uselist=False))
'''
