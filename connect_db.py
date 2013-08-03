from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from bizarro.models.stats import *

def this_engine(alt=True):
    engine = create_engine('sqlite:////home/tignas/pyramid/bizarro/bizarro.sqlite', echo=False)
    return engine

def create_session(alt=False):
    if alt:
        engine = this_engine(True)
    else:
        engine = this_engine(True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session
    
def delete_table(table):
    engine = this_engine()
    table = DDL('DROP TABLE %s' % table)
    engine.execute(table)
    
def add_column(table, column_name, column_type):
    engine = this_engine()
    new_column = DDL('ALTER TABLE %s ADD COLUMN %s %s' % (table, column_name, 
                                                    column_type))
    engine.execute(new_column)
        
def get_or_create(session, model, defaults=None, **kwargs):
    try:
        instance = session.query(model).filter_by(**kwargs).one()
        return instance, False
    except NoResultFound:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance, True
    except MultipleResultsFound:
        instances = session.query(model).filter_by(**kwargs).all()
        print instances
        raise Exception('too many found')
        
def get_and_delete(session, model, defaults=None, **kwargs):
    try:
        instance = session.query(model).filter_by(**kwargs).one()
        session.delete(instance)
        session.commit()
        return False
    except NoResultFound:
        return True
        
def save(session, instance):
    session.add(instance)
    session.commit()
    return instance
    
def delete_game(game_id):
    session = create_session()
    models = [GameTeamScore, GameOfficial, GamePlayer, PlayerStat,
              FootballTeamStat, BasketballTeamStat]
    for model in models:
        q = session.query(model).filter_by(game_id=game_id).delete()
    q = session.query(Game).filter_by(id=game_id).delete()
    session.commit()
    q = session.query(GameExternalID).filter_by(game_id=game_id).all()
    if len(q) > 1:
        for p in q[1:]:
            delete(p)
    elif len(q) == 1:
        q[0].game_id = None
    session.commit()
    print 'deleted game'
    
    
    
    
    
    
    
    
    
    
    
    
    
