from meta import *
from stats import Season, Game, ExternalID
from sqlalchemy import func
from sqlalchemy.orm import eagerload, column_property

class Location(Base):
    id = Column(Integer, primary_key=True)
    city = Column(String)
    state = Column(String)
    town = Column(String)
    county = Column(String)
    neighborhood = Column(String)
    sublocality = Column(String)
    country = Column(String)
    timezone = Column(String)
    latitude = Column(Integer)
    longitude = Column(Integer)
    
    def __repr__(self):
        return '%s %s' % (self.city, self.state)
    
class Address(Base):
    id = Column(Integer, primary_key=True)
    suite = Column(String)
    floor = Column(String)
    building = Column(String)
    street_number = Column(Integer)
    street_prefix = Column(String)
    street = Column(String)
    street_suffix = Column(String)
    postal_code = Column(String)
    location_id = Column(Integer, ForeignKey('location.id'))
    
    location = relationship('Location')
    
    def __repr__(self):
        return '%s %s %s %s' % (self.street_number, self.street, self.location, 
                                self.postal_code)

class Sport(Base):
    name = Column(String, primary_key=True)  
      
    def __repr__(self):
        return '%s' % (self.name)

    def url(self):
        return '/%s/' % self.name
    
class League(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    abbr = Column(String)
    website = Column(String)
    motto = Column(String)
    founded_location_id = Column(Integer, ForeignKey('location.id'))
    address_id = Column(Integer, ForeignKey('address.id'))
    sport_name = Column(String, ForeignKey('sport.name'))
    
    sport = relationship('Sport', uselist=False)
    teams = relationship('Team', secondary='league_team')
    
    def __repr__(self):
        return '%s' % (self.abbr)
        
    def url(self):
        return '/%s/%s/' % (self.sport_name, self.abbr)
        
    def seasons(self):
        session = DBSession()
        seasons = session.query(Season.year)\
                         .join(League)\
                         .filter(League.abbr==self.abbr)\
                         .order_by(-Season.year)\
                         .all()
        return seasons
        
    @classmethod
    def links(cls):
        return ['standings', 'stats', 'schedule']
        
    
class Division(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    league_id = Column(Integer, ForeignKey('league.id'))
    
    league = relationship('League', backref=backref('divisions'))
    conference = relationship('Conference', 
                              secondary='division_conference', uselist=False,
                              backref=backref('divisions', lazy='joined'),)
    teams = relationship('Team', secondary='division_team', lazy='joined',
                            backref=backref('division', uselist=False))
                            
    def __repr__(self):
        name = self.name if self.name else self.abbr
        return '%s' % (name)

class Conference(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    league_id = Column(Integer, ForeignKey('league.id'))
    
    league = relationship('League', backref=backref('conference'))
    
    def __repr__(self):
        return '%s' % (self.abbr)

class DivisionConference(DateMixin, Base):
    division_id = Column(Integer, ForeignKey('division.id'), primary_key=True)
    conference_id = Column(Integer, ForeignKey('conference.id'), 
                           primary_key=True)
    
    def __repr__(self):
        return '%s' % (self.conference, self.division)

class DivisionTeam(DateMixin, Base):
    division_id = Column(Integer, ForeignKey('division.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)
    
    def __repr__(self):
        return '%s' % (self.team, self.division)

class Team(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    location = Column(String)
    sport_name = Column(String, ForeignKey('sport.name'))
    full_name = column_property(location + " " + name)
    
    sport = relationship('Sport', uselist=False)
    league = relationship('League', secondary='league_team', 
                           uselist=False, lazy='joined')
    team_names = relationship('TeamName')
    team_locations = relationship('TeamLocation')
    team_nicknames = relationship('TeamNickname')
    players = relationship('Player', secondary='team_player')
    roster = relationship('Player', secondary='team_player', 
                          secondaryjoin='and_(TeamPlayer.player_id==Player.id,' 
                                              'TeamPlayer.current==True)')
    
    @classmethod
    def links(self):
        links = ['roster', 'stats', 'schedule', 'depth_chart', 'news']
        return links
        
    @classmethod
    def full_links(self):
        '''
        links = ['schedule', 'roster', 'news', 'stats', 'splits', 
                        'depth chart', 'rankings', 'transactions', 'media', 
                        'stadium', 'forum']
        '''
        links = ['roster', 'schedule', 'stats']
        return links
    
    def __repr__(self):
        return '%s %s' % (self.location, self.name)
        
    def team_names_list(self):
        names = [name.name for name in self.team_names]
        return names
        
    def team_locations_list(self):    
        names = [name.name for name in self.team_locations]
        return names
        
    def team_nicknames_list(self):    
        names = [name.name for name in self.team_nicknames]
        return names
    
    def all_names(self):
        return self.team_names_list() + self.team_locations_list() + \
               self.team_nicknames_list() + \
               [self.name, self.location, self.abbr]                        
               
    def url(self):
        return '/%s/%s/teams/%s/' % (self.sport_name, self.league.abbr, 
                                     self.abbr)
        
    @classmethod
    def home_wins(cls, **kw):
        return DBSession.query(Game.id, Game.home_team_id, 
                               func.count(Game.id).label('home_wins'))\
                        .filter(Game.home_score>Game.away_score,
                                Game.game_type==kw['game_type'],
                                Game.season.has(year=kw['season']))\
                        .group_by(Game.home_team_id)\
                        .subquery()
    
    @classmethod
    def home_loss(cls, **kw):
        return DBSession.query(Game.id, Game.home_team_id, 
                               func.count(Game.id).label('home_loss'))\
                        .join(Season)\
                        .filter(Game.home_score<Game.away_score,
                                Game.game_type==kw['game_type'],
                                Game.season.has(year=kw['season']))\
                        .group_by(Game.home_team_id)\
                        .subquery() 
    
    @classmethod
    def away_wins(cls, **kw):
        return DBSession.query(Game.id, Game.away_team_id, 
                               func.count(Game.id).label('away_wins'))\
                        .join(Season)\
                        .filter(Game.home_score<Game.away_score,
                                Game.game_type==kw['game_type'],
                                Game.season.has(year=kw['season']))\
                        .group_by(Game.away_team_id)\
                        .subquery()
                        
    @classmethod
    def away_loss(cls, **kw):
        return DBSession.query(Game.id, Game.away_team_id, 
                               func.count(Game.id).label('away_loss'))\
                        .join(Season)\
                        .filter(Game.home_score>Game.away_score,
                                Game.game_type==kw['game_type'],
                                Game.season.has(year=kw['season']))\
                        .group_by(Game.away_team_id)\
                        .subquery()
        
    
    @classmethod
    def season_wins(cls, **kw):
        hw = cls.home_wins(**kw)
        hl = cls.home_loss(**kw)
        aw = cls.away_wins(**kw)
        al = cls.away_loss(**kw)
        return DBSession.query(cls, hw, hl, aw, al)\
                       .options(eagerload('league'),
                                eagerload('division'),
                                eagerload('division.conference'))\
                       .filter(Team.league==kw['league'])\
                       .outerjoin(hw, hw.c.home_team_id==Team.id)\
                       .outerjoin(hl, hl.c.home_team_id==Team.id)\
                       .outerjoin(aw, aw.c.away_team_id==Team.id)\
                       .outerjoin(al, al.c.away_team_id==Team.id)
                       
    @classmethod
    def get_team(cls, league, team_abbr):
        return DBSession.query(cls)\
                        .filter(Team.abbr==team_abbr,
                                Team.league==league)
    
    @classmethod
    def get_roster(cls, t_query):
        return t_query.options(eagerload('roster'),
                               eagerload('roster.number'),
                               eagerload('roster.person.college'),
                               eagerload('roster.person.height_weight'))
                               
class LeagueTeam(DateMixin, Base):
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)
    league_id = Column(Integer, ForeignKey('league.id'), primary_key=True)
        
class TeamName(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team', backref=backref('names'))
    
    def __repr__(self):
        return '%s' % (self.abbr)

class TeamNickname(Base):
    name = Column(String, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)
    
    team = relationship('Team', backref=backref('nicknames')) 
        
    def __repr__(self):
        return '%s' % (self.name)

class TeamLocation(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location_id = Column(Integer, ForeignKey('location.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    
    def __repr__(self):
        return '%s' % (self.location, self.team)
    
class Venue(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    broke_ground_date = Column(Date)
    address_id = Column(Integer, ForeignKey('address.id'))
    
    address = relationship('Address')
    capacity = relationship('VenueCapacity')
    
class VenueCapacity(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    capacity = Column(Integer)
    sport_name=Column(String, ForeignKey('sport.name'))
    venue_id = Column(Integer, ForeignKey('venue.id'))

class TeamVenue(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venue.id'))
    team_id = Column(Integer, ForeignKey('team.id'))    
    
class VenueName(DateMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    abbr = Column(String)
    venue_id = Column(Integer, ForeignKey('venue.id'))

class TeamExternalID(ExternalID):
    team_id = Column(Integer, ForeignKey('team.id'))

    team = relationship('Team')
    
    __mapper_args__ = {'polymorphic_identity': 'team', 'concrete': True}

    
