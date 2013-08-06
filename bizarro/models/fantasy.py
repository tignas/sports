import numpy
from collections import OrderedDict
from itertools import groupby
from meta import *
from media import *
from people import Player
from stats import Season
from apex.models import AuthID

class FantasyRanking(MediaItem):
    id = Column(Integer, ForeignKey('media_item.id'), primary_key=True)
    ranking_type = Column(String)
    league_id = Column(Integer, ForeignKey('league.id'))
    season_id = Column(Integer, ForeignKey('season.id'))
    writer_id = Column(Integer, ForeignKey('writer.id'))
    week = Column(Integer)
    position = Column(Integer, ForeignKey('position.id'))
    
    writer = relationship('Writer')
    rankings = relationship('FantasyRank', order_by='FantasyRank.rank')
    
    __mapper_args__ = {'polymorphic_identity': 'fantasy_ranking'}

class FantasyRank(Base):
    fantasy_ranking_id = Column(Integer, 
                               ForeignKey('fantasy_ranking.id'), 
                               primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), primary_key=True)
    rank = Column(Integer)
    
    player = relationship('Player')
    
class Projection(Base):
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    updated = Column(DateTime)
    source_name = Column(String, ForeignKey('source.name'))
    season_id = Column(Integer, ForeignKey('season.id'))
    league_id = Column(Integer, ForeignKey('league.id'))
    writer_id = Column(Integer, ForeignKey('writer.id'))
    
    projections = relationship('IndividualProjection', backref='projection')
    league = relationship('League', uselist=False)
    writer = relationship('Writer', uselist=False, lazy='joined')
    season = relationship('Season', uselist=False)
    
class IndividualProjection(Base):
    id = Column(Integer, primary_key=True)
    projection_id = Column(Integer, ForeignKey('projection.id'))
    projection_type = Column(String)
    
    __mapper_args__ = {'polymorphic_on': projection_type,
                       'with_polymorphic':'*'}
                       
    @classmethod
    def projections(cls, player, season):
        return DBSession.query(cls)\
                        .join(Projection, Season)\
                        .filter(cls.player==player,
                                Season.year==season)
                                
    @classmethod
    def average(cls, projs):
        projs = [p.as_dict() for p in projs]
        return {abbr: int(round(numpy.mean([p.get(cat.name) or 0 
                                        for p in projs])))
                for cat, abbr in cls.abbr()}
    
class TeamDefenseProjection(IndividualProjection):
    id = Column(Integer, ForeignKey('individual_projection.id'), 
                primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'))
    sacks = Column(Integer)
    safeties = Column(Integer)
    interceptions = Column(Integer)
    fumbles_forced = Column(Integer)
    fumbles_recovered = Column(Integer)
    touchdowns = Column(Integer)
    points_against = Column(Integer)
    yards_against = Column(Integer)
    fantasy_points = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'defense'}
    
    team = relationship('Team', lazy='joined')
    
    def __repr__(self):
        return '%s' % self.team
    
class FootballOffenseProjection(IndividualProjection):
    id = Column(Integer, ForeignKey('individual_projection.id'), 
                primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    passing_attempts = Column(Integer)
    passing_completions = Column(Integer)
    passing_yards = Column(Integer)
    passing_touchdowns = Column(Integer)
    passing_interceptions = Column(Integer)
    rushing_attempts = Column(Integer)
    passing_sacks = Column(Integer)
    rushing_yards = Column(Integer)
    rushing_touchdowns = Column(Integer)
    receiving_yards = Column(Integer)
    receiving_touchdowns = Column(Integer)
    receiving_receptions = Column(Integer)
    receiving_targets = Column(Integer)
    fumbles_total = Column(Integer)
    fumbles_lost = Column(Integer)
    two_pt = Column(Integer)
    return_yards = Column(Integer)
    return_touchdowns = Column(Integer)
    
    player = relationship('Player', lazy='joined')
        
    __mapper_args__ = {'polymorphic_identity': 'offense'}
    
    def __repr__(self):
        return '%s' % self.player
        
    @classmethod
    def abbr(cls):
        return [
            (cls.passing_completions, 'pass_comp'),
            (cls.passing_attempts, 'pass_att'),
            (cls.passing_yards, 'pass_yd'),
            (cls.passing_interceptions, 'pass_int'),
            (cls.passing_touchdowns, 'pass_td'),
            (cls.passing_sacks, 'pass_sk'),
            (cls.rushing_attempts, 'rush_att'),
            (cls.rushing_yards, 'rush_yd'),
            (cls.rushing_touchdowns, 'rush_td'),
            (cls.receiving_receptions, 'rec_rec'),
            (cls.receiving_targets, 'rec_tgt'),
            (cls.receiving_yards, 'rec_yd'),
            (cls.receiving_touchdowns, 'rec_td'),
            (cls.return_yards, 'ret_yd'),
            (cls.return_touchdowns, 'ret_td'),
            (cls.fumbles_total, 'fum_tot'),
            (cls.fumbles_lost, 'fum_lost'),
            (cls.two_pt, '2pt'),
        ]
        
    @classmethod
    def grouped_headers(cls):
        headers = OrderedDict()
        [headers.update({cat.split('_')[0]:headers.get(cat.split('_')[0], 0) + 1}) 
            for full, cat in cls.abbr()]
        return headers
    
class FootballKickingProjection(IndividualProjection):
    id = Column(Integer, ForeignKey('individual_projection.id'), 
                primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    u_40_make = Column(Integer)
    u_40_miss = Column(Integer)
    o_50_make = Column(Integer)
    o_50_miss = Column(Integer)
    b_40_50_make = Column(Integer)
    b_40_50_miss = Column(Integer)
    xp_make = Column(Integer)
    xp_miss = Column(Integer)
    
    player = relationship('Player', lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity': 'kicking'}
    
    def __repr__(self):
        return '%s' % self.player
        
class UserProjection(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(Text)
    auth_id = Column(Integer, ForeignKey(AuthID.id), index=True)

    user = relationship(AuthID, uselist=False)
'''
class FantasyLeague(Base):
    id = Column(Integer, primary_key=True)

class FantasyRoster(Base):
    id = Column(Integer, primary_key=True)
    qb = Column(Integer)
    rb = Column(Integer)
    wr = Column(Integer)
    te = Column(Integer)
    pk = Column(Integer)
    dst = Column(Integer)
    ben = Column(Integer)

class FantasyScoring(Base):
    id = Column(Integer, primary_key=True)
    pass_att = Column(Integer)
    pass_comp = Column(Integer)
    pass_yd = Column(Integer)
    pass_td = Column(Integer)
    pass_int = Column(Integer)
    pass_sk = Column(Integer)
    rush_att = Column(Integer)
    rush_yd = Column(Integer)
    rush_td = Column(Integer)
    rec_rec = Column(Integer)
    rec_yd = Column(Integer)
    rec_td = Column(Integer)
    fum_tot = Column(Integer)
    fum_lost = Column(Integer)
    ret_yd = Column(Integer)
    ret_td = Column(Integer)
    xp_make = Column(Integer)
    xp_miss = Column(Integer)
    fg_make = Column(Integer)
    fg_miss = Column(Integer)
    o_50_make = Column(Integer)
    o_50_miss = Column(Integer)
    def_int = Column(Integer)
    def_td = Column(Integer)
    def_fum = Column(Integer)
    def_safe = Column(Integer)
    def_sk = Column(Integer)
'''
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
