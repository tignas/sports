from itertools import groupby
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import column_property, eagerload, aliased
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import select, exists
from meta import *
from media import Source
from teams import Team
from stats import ExternalID, BasketballBoxScoreStat, Game, Season, PlayerStat, GamePlayer, FootballPuntingStat

class Person(Base):
    id = Column(Integer, primary_key=True)
    birth_name = Column(String)
    dob = Column(Date)
    birth_location = Column(Integer, ForeignKey('location.id'))
    
    height_weight = relationship('HeightWeight', uselist=False)
    college = relationship('College', secondary='college_person')
    names = relationship('PersonName', lazy='joined')
    
    def __repr__(self):
        return '%s' % (self.names[0])
        
class PersonName(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'))
    full_name = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    prefix = Column(String)
    suffix = Column(String)
        
    person = relationship('Person', uselist=False)
    middle_names = relationship('MiddleName')
    
    def slugify(self):
        return self.full_name.lower().replace(' ', '+')
        
    def __repr__(self):
        return '%s' % (self.full_name)
    
class MiddleName(DateMixin, Base):
    person_name_id = Column(Integer, ForeignKey('person_name.person_id'),
                            primary_key=True)
    middle_name = Column(String, primary_key=True)

class LeaguePerson(AbstractConcreteBase, Base):
    id = Column(Integer, primary_key=True)
    
    @declared_attr
    def league_id(cls):
        return Column(Integer, ForeignKey('league.id'))
    
    @declared_attr
    def person_id(cls):
        return Column(Integer, ForeignKey('person.id'))
        
    @declared_attr
    def league(cls):
        return relationship('League', lazy='joined')
        
    @declared_attr
    def person(cls):
        return relationship('Person', lazy='joined')

class Official(LeaguePerson): 
    number = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'official', 'concrete': True}
    
    def __repr__(self):
        return 'official %s' % (self.person)

class Coach(LeaguePerson):
        
    __mapper_args__ = {'polymorphic_identity': 'coach', 'concrete': True}
    
    def url(self):
        return ''
    
class Player(LeaguePerson):
    
    positions = relationship('Position', secondary='player_position', 
                             lazy='joined')
    number = relationship('PlayerNumber')
    teams = relationship('Team', secondary='team_player')
    team = relationship('Team', secondary='team_player', 
                        order_by='-TeamPlayer.current', uselist=False, 
                        lazy='joined')
    
    def position_string(self):
        position_string = ''
        for position in self.positions:
            position_string += '%s/' % position.abbr
        return position_string[:-1]
        
    '''
    
    @hybrid_property
    def current(self):
        return DBSession.query(exists().where(and_(TeamPlayer.current==True, TeamPlayer.player_id==self.id))).scalar()
    '''
        
    @classmethod
    def current_players(cls, league):
        return DBSession.query(cls)\
                        .join(Person, PersonName)\
                        .options(eagerload('person.height_weight'),
                                 eagerload('person.college'))\
                        .join(TeamPlayer)\
                        .filter(TeamPlayer.current==True, 
                                Player.league==league)\
                        .order_by(PersonName.full_name)
    @classmethod
    def links(self):
        '''
        return ['stats', 'profile', 'graph', 'rankings', 'injury', 
                'news', 'photos', 'videos', 'awards', 'advanced_stats', 
                'shopping', 'projections', 'fantasy']
        '''
        return ['stats', 'projections', 'fantasy']     
    
    @classmethod
    def get_current(cls):
        players = DBSession.query(cls).first()
        return players
     
    def __repr__(self):
        return '%s %s %s' % (self.league, self.position_string(), self.person)
        
    def url(self):
        url = '/%s/%s/player/%d/%s/' 
        url %= (self.league.sport_name, self.league.abbr, 
                self.id, self.person.names[0])
        return url
        
    @classmethod
    def stats(cls, sport, league, game_type, season, queries, q=None):
        stats = [DBSession.query(model.player_id, *query)\
                           .join(Game, Season)\
                           .filter(Game.game_type==game_type, 
                                   Season.year==season)\
                           .group_by(model.player_id)\
                           .subquery()
                    for model, query in queries]
        gp = DBSession.query(GamePlayer.player_id, *GamePlayer.sum_query())\
                           .join(Game, Season)\
                           .filter(Game.game_type==game_type, 
                                   Season.year==season,
                                   GamePlayer.status!='dnp')\
                           .group_by(GamePlayer.player_id)\
                           .subquery()
        stats.append(gp)
        p = DBSession.query(cls, *stats)\
                     .options(eagerload('positions'))\
                     .join(TeamPlayer, Team)
        for s in stats:
            p = p.outerjoin(s)
        p = p.filter(cls.league==league).group_by(cls)
        if q:
            p = p.having(or_(stats[0].c[q] > 0, stats[0].c[q] > 1))
        else:
            p = p.having(gp.c.gp > 0)
        return p
    
    @classmethod
    def stats_by_season(cls, game_stats):
        key = lambda x: x.__class__
        stats_by_type = groupby(sorted(list(game_stats), key=key), key=key)
        stats = {}
        for model, stat_list in stats_by_type:
            stat_type = model.__mapper_args__['polymorphic_identity']
            key = lambda x:x.game.season.year
            season_stats = groupby(sorted(list(stat_list), key=key, reverse=True), key=key)
            stats[stat_type] = []
            for season, season_stat_list in season_stats:
                d = {}
                d['season'] = season
                d['games'] = list(season_stat_list)
                season_stat_list = [stat.as_dict() for stat in d['games']]
                totals = {abbr: sum(stat.get(cat.name) or 0 
                                        for stat in season_stat_list) 
                            for cat, abbr in model.abbr()}
                d['totals'] = totals
                stats[stat_type].append(d)
        return stats
        
    __mapper_args__ = {'polymorphic_identity': 'player', 'concrete': True}
   
class TeamPersonnel(AbstractConcreteBase, DateMixin, Base):
    id = Column(Integer, primary_key=True)
    current = Column(Boolean)
    
    @declared_attr
    def team_id(cls):
        return Column(Integer, ForeignKey('team.id'))
    
    @declared_attr
    def team(cls):
        return relationship('Team', uselist=False)
                               
class TeamPlayer(TeamPersonnel):
    player_id = Column(Integer, ForeignKey('player.id'))
    
    player = relationship('Player', uselist=False)    
    
    __mapper_args__ = {'polymorphic_identity': 'player', 'concrete': True}

class TeamCoach(TeamPersonnel):
    coach_id = Column(Integer, ForeignKey('coach.id'))
    coach_type = Column(String)
    
    coach = relationship('Coach', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity': 'coach', 'concrete': True}
    
class PlayerNumber(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    number = Column(Integer)    
    
    player = relationship('Player')
    
    def __repr__(self):
        return '%d' % self.number        

class PlayerPosition(Base):
    player_id = Column(Integer, ForeignKey('player.id'), primary_key=True)
    position_id = Column(Integer, ForeignKey('position.id'), primary_key=True)
   
class Position(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    sport_name = Column(String, ForeignKey('sport.name'))
    
    def __repr__(self):
        return '%s' % self.abbr

class HeightWeight(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'))
    height = Column(Integer)
    weight = Column(Integer)
    
    def feet_inches(self):
        if self.height:
            feet = self.height/12
            inches = self.height%12
            return '%d\' %d"' % (feet, inches)
        else:
            return '-'
    
class CollegePerson(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'))
    college_name = Column(String, ForeignKey('college.name'))
    
class College(Base):
    name = Column(String, primary_key=True)
    abbr = Column(String)
    location_id = Column(Integer, ForeignKey('location.id'))
    
    location = relationship('Location')  
    
    def __repr__(self):
        return '%s' % self.name
        
class PlayerExternalID(ExternalID):
    player_id = Column(Integer, ForeignKey('player.id'))
    
    player = relationship('Player', backref='espn_id')
    
    __mapper_args__ = {'polymorphic_identity': 'player', 'concrete': True}
    
    def __repr__(self):
        return '%s %s' % (self.player, self.external_id)
    
class CoachExternalID(ExternalID):
    coach_id = Column(Integer, ForeignKey('coach.id'))

    coach = relationship('Coach')
    
    __mapper_args__ = {'polymorphic_identity': 'coach', 'concrete': True}
    
