import re
from sqlalchemy import and_, or_, desc, not_
from sqlalchemy.ext.declarative import (declarative_base, declared_attr, 
                                        AbstractConcreteBase)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.util import polymorphic_union

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    Date,
    Boolean,
    DateTime,
    Time,
    Interval,
    String,
   )
   
class Base(object):
    @declared_attr
    def __tablename__(cls):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
    def as_dict(self):
        row_dict = lambda self: {c.name: getattr(self, c.name) 
                              for c in self.__table__.columns}
        return row_dict(self)
        
    @classmethod
    def get(cls, **kwargs):
        return DBSession.query(cls).filter_by(**kwargs)
        
    @classmethod
    def get_one(cls, **kwargs):
        return DBSession.query(cls).filter_by(**kwargs).one()
        
    @classmethod
    def get_all(cls, **kwargs):
        return DBSession.query(cls).filter_by(**kwargs).all()
        
Base = declarative_base(cls=Base)
DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
    
class DateMixin(object):
    start_date = Column(Date)
    end_date = Column(Date)
    
    
    
    
