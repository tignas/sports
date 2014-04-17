import time
import datetime
from collections import OrderedDict
from itertools import groupby, ifilter, ifilterfalse
from meta import *
from media import Network
from sqlalchemy import Index
from sqlalchemy.orm import column_property, eagerload, aliased
from sqlalchemy import select, func
        
class ExternalID(AbstractConcreteBase, Base):
    id = Column(Integer, primary_key=True)
    external_id = Column(String)
    
    @declared_attr
    def source_name(cls):
        return Column(Integer, ForeignKey('source.name'))
        
    @declared_attr
    def league_id(cls):
        return Column(Integer, ForeignKey('league.id'))
        
    @declared_attr
    def league(cls):
        return relationship('League', uselist=False)
        
class Season(Base):
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey('league.id'), index=True)
    year = Column(Integer)
    preseason_start = Column(Date)
    preseason_end = Column(Date)
    regular_start = Column(Date)
    regular_end = Column(Date)
    postseason_start = Column(Date)
    postseason_end = Column(Date)
    
    league = relationship('League')
    
    def __repr__(self):
        return '%s - %s' % (self.league, self.year)

class GameTeamScore(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), index=True)
    team_id = Column(Integer, ForeignKey('team.id'), index=True)
    period = Column(Integer)
    score = Column(Integer)
    
    team = relationship('Team', uselist=False)
    game = relationship('Game', uselist=False)
    
    def __repr__(self):
        return '%s - %d' % (self.team, self.score)
   
class Game(Base):
    id = Column(Integer, primary_key=True)
    game_time = Column(DateTime)
    game_type = Column(String)
    attendance = Column(Integer)
    duration = Column(Time)
    season_id = Column(Integer, ForeignKey('season.id'), index=True)
    home_team_id = Column(Integer, ForeignKey('team.id'), index=True)
    away_team_id = Column(Integer, ForeignKey('team.id'), index=True)
    league_id = Column(Integer, ForeignKey('league.id'), index=True)
    venue_id = Column(Integer, ForeignKey('venue.id'))
    network_abbr = Column(Integer, ForeignKey('network.abbr'))
    
    home_score = column_property(
        select([func.sum(GameTeamScore.score)])\
            .where(and_(GameTeamScore.team_id==home_team_id, 
                        GameTeamScore.game_id==id))
    )
    away_score = column_property(
        select([func.sum(GameTeamScore.score)])\
            .where(and_(GameTeamScore.team_id==away_team_id, 
                        GameTeamScore.game_id==id))
    )
    
    espn_id = relationship('GameExternalID', uselist=False)
    league = relationship('League', uselist=False)
    home_team = relationship('Team', 
                             primaryjoin='Game.home_team_id==Team.id', 
                             uselist=False)
    away_team = relationship('Team', 
                             primaryjoin='Game.away_team_id==Team.id', 
                             uselist=False)
    home_scores = relationship('GameTeamScore', primaryjoin='and_'
                               '(Game.id==GameTeamScore.game_id,' 
                               'Game.home_team_id==GameTeamScore.team_id)',
                               order_by='GameTeamScore.period',
                               cascade='all,delete')
    away_scores = relationship('GameTeamScore', primaryjoin='and_'
                               '(Game.id==GameTeamScore.game_id,' 
                               'Game.away_team_id==GameTeamScore.team_id)',
                                order_by='GameTeamScore.period',
                                cascade='all,delete')
    season = relationship('Season', uselist=False)
    venue = relationship('Venue', uselist=False)
    game_players = relationship('GamePlayer')
    players = relationship('Player', secondary='game_player', 
                            cascade='all,delete')
    officials = relationship('Official', secondary='game_official', 
                              cascade='all,delete')
    stats = relationship('PlayerStat', cascade='all,delete')
    
    @classmethod
    def links(self):
        game_links = ['boxscore']
        #game_link += ['plays', 'shots', 'conversation', 'media']
        return game_links
        
    @classmethod
    def game_types(self):        
        game_types_dict = {
            'pre': 'preseason',
            'reg': 'regular',
            'post': 'postseason',
        }
        return game_types_dict
        
    @classmethod
    def get_game(cls, game_id):
        return DBSession.query(cls)\
                        .options(eagerload('away_team'),
                                 eagerload('home_team'),
                                 eagerload('home_scores'),
                                 eagerload('away_scores'),
                                 eagerload('officials'),)\
                        .get(game_id)
        
    @classmethod
    def get_date(cls, league, date):
        day = datetime.timedelta(days=1)
        return DBSession.query(cls)\
                       .options(eagerload('home_scores'),
                                eagerload('away_scores'),
                                eagerload('home_team'),
                                eagerload('away_team'),
                                eagerload('league'))\
                       .filter(cls.league==league,
                               cls.game_time.between(date, date+day))\
                       .order_by(cls.game_time)\
                       .all()
                       
    @classmethod
    def get_season(cls, league, game_type, year):
        return DBSession.query(cls)\
                       .options(eagerload('away_team'),
                                eagerload('home_team'),
                                eagerload('home_scores'),
                                eagerload('away_scores'),
                                eagerload('season'),
                                eagerload('league'),
                                eagerload('away_team.league'),
                                eagerload('home_team.league'))\
                       .filter(cls.league==league, 
                               cls.game_type==game_type,
                               cls.season.has(year=year))\
                       .order_by(cls.game_time)
    
    def periods(self):
        periods = len(self.home_scores)
        periods_list = []
        for period in range(1, periods+1):
            if period > 4:
                period -= 4
                period = '%d OT' % period
            else:
                period = '%d' % period
            periods_list.append(period)
        return periods_list
        
    def num_periods(self):
        periods = len(self.home_scores)
        return periods
        
    def winner(self):
        if self.away_score > self.home_score:
            team = self.away_team
        elif self.away_score == self.home_score:
            team = None
        else:
            team = self.home_team
        return team
        
    def week(self):
        difference = self.game_time.date() - self.season.regular_start
        week = difference.days / 7 + 1
        return week
        
    def __repr__(self):
        return '%s @ %s %s' % (self.away_team.abbr, self.home_team.abbr, 
                               self.game_time.strftime('%m/%d/%y %I:%M %p'))
                               
    def url(self):
        return '/%s/%s/games/%d/' % (self.league.sport_name, 
                                     self.league.abbr, self.id)
                                     
    @classmethod
    def sorted_stats(cls, players):
        key = lambda x: x.team
        stats = groupby(sorted(list(players), key=key), key=key)
        stats = {team: list(players) for team, players in stats}
        stats = {team: {
                    'starter': [p for p in players if p.starter],
                    'bench': [p for p in players 
                                if not p.starter and not p.status == 'dnp'], 
                    'dnp': [p for p in players if p.status == 'dnp'],
                 } for team, players in stats.iteritems()}
        return stats
        
    @classmethod
    def team_schedule(cls, team, game_type, year):
        return DBSession.query(cls)\
                        .options(eagerload('away_team'),
                                eagerload('home_team'),
                                eagerload('home_scores'),
                                eagerload('away_scores'),)\
                        .filter(or_(cls.home_team==team, 
                                   cls.away_team==team),
                               cls.game_type==game_type,
                               cls.season.has(year=year))\
                        .order_by(Game.game_time)

class GameOfficial(Base):
    game_id = Column(Integer, ForeignKey('game.id'), primary_key=True)
    official_id = Column(Integer, ForeignKey('official.id'), primary_key=True)
    official_type = Column(String)
    
    official = relationship('Official', uselist=False)
    game = relationship('Game', uselist=False)
    
class GameExternalID(ExternalID):
    game_id = Column(Integer, ForeignKey('game.id'))
    boxscore = Column(Boolean)
    shot_cords = Column(Boolean)
    pbp = Column(Boolean)
    
    game = relationship('Game')
    
    __mapper_args__ = {'polymorphic_identity': 'game', 'concrete': True}
    
    def __repr__(self):
        return '%s' % self.external_id
       
class GamePlayer(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), index=True)
    team_id = Column(Integer, ForeignKey('team.id'), index=True)
    player_id = Column(Integer, ForeignKey('player.id'), index=True)
    starter = Column(Boolean)
    status = Column(String)
    
    game = relationship('Game', uselist=False)
    player = relationship('Player', uselist=False)
    team = relationship('Team', uselist=False)
    stats = relationship('PlayerStat', 
                    primaryjoin='and_('
                                'GamePlayer.player_id==PlayerStat.player_id,'
                                'GamePlayer.team_id==PlayerStat.team_id,'
                                'GamePlayer.game_id==PlayerStat.game_id)',
                    foreign_keys=[game_id, team_id, player_id])
    
    
    @classmethod
    def sum_query(cls):
        sum_query = [
            func.count(cls.game_id).label('gp')
        ]
        return sum_query
    
    @classmethod
    def dnps(cls, game):
        return DBSession.query(cls)\
                        .options(eagerload('player'),
                                 eagerload('player.positions'),
                                 eagerload('team'),
                                 eagerload('team.league'))\
                       .join(GamePlayerDNP)\
                       .filter(cls.game==game)
                       
    @classmethod
    def get_game(cls, game):
        return DBSession.query(GamePlayer)\
                        .options(eagerload('player'),
                                 eagerload('team'))\
                        .filter(GamePlayer.game==game)
    
    def __repr__(self):
        return '%s %s' % (self.player, self.game)

class GamePlayerDNP(Base):
    id = Column(Integer, ForeignKey('game_player.id'), primary_key=True)
    reason = Column(String)
    
    game_player = relationship('GamePlayer', uselist=False, lazy='joined',
                                backref=backref('dnp', lazy='joined', 
                                                uselist=False))

    
class PlayerStat(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'), index=True)
    team_id = Column(Integer, ForeignKey('team.id'), index=True)
    player_id = Column(Integer, ForeignKey('player.id'), index=True)
    stat_type = Column(String)
    
    game = relationship('Game', uselist=False)
    player = relationship('Player', uselist=False)
    team = relationship('Team', uselist=False)
    
    __mapper_args__ = {'polymorphic_on': stat_type}
    
    @classmethod
    def model_map(cls, sport, stat_type=None):
        map_ = {
            'football': OrderedDict([
                ('passing', FootballOffensiveStat),
                ('rushing', FootballOffensiveStat),
                ('receiving', FootballOffensiveStat),
                ('return', FootballOffensiveStat),
                ('kicking', FootballKickingStat),
                ('punting', FootballPuntingStat),
                #('defense', FootballTeamStat),
            ]),
            'basketball': BasketballBoxScoreStat,
        }
        if stat_type:
            return map_[sport][stat_type]
        else:
            return map_[sport]
            
    @classmethod
    def full_map(cls):
        return OrderedDict([
                ('passing', FootballPassingStat),
                ('rushing', FootballRushingStat),
                ('receiving', FootballReceivingStat),
                ('fumble', FootballFumbleStat),
                ('return', FootballReturnStat),
                ('kicking', FootballKickingStat),
                ('punting', FootballPuntingStat),
                ('interception', FootballInterceptionStat),
                ('defensive', FootballDefensiveStat),
            ])
            
    @classmethod
    def queries(cls, sport, stat_type):
        q = []
        if sport == 'basketball':
            q.append(BasketballBoxScoreStat, BasketballBoxScoreStat.sum_query())
        return q
        
    @classmethod
    def player_stats(cls, sport, league, game_type, player):
        stats = DBSession.query(cls)\
                         .options(eagerload('game'), 
                                  eagerload('game.season'))\
                         .with_polymorphic('*')\
                         .join(Game)\
                         .filter(cls.player==player,
                                 cls.stat_type!='offense',
                                 Game.game_type==game_type)
        return stats
        
    @classmethod
    def get_game(cls, game):
        return DBSession.query(cls)\
                        .options(eagerload('player'),
                                 eagerload('team'))\
                        .with_polymorphic('*')\
                        .filter(cls.game_id==game.id)\
                        .all()
    
    @classmethod
    def sorted_game_stats(cls, stats):
        key = lambda x: x.team
        stats = groupby(sorted(list(stats), key=key), key=key)
        stats = {team:list(stats) for team, stats in stats}
        game_stats = {}
        for team, stat_list in stats.iteritems():
            game_stats[team] = {}
            key = lambda x: x.stat_type
            stat_list = sorted(stat_list, key=key)
            for stat_type, these_stats in groupby(stat_list, key=key):
                if stat_type == 'return':
                    game_stats[team]['kick_return'] = []
                    game_stats[team]['punt_return'] = []
                    for stat in list(these_stats):
                        return_type = '%s_return' % stat.return_type
                        game_stats[team][return_type].append(stat)
                else:
                    game_stats[team][stat_type] = list(these_stats)
        return game_stats 
    
    @classmethod
    def player_sum(cls, sport, league, game_type, player, season):
        return DBSession.query(*cls.sum_query())\
                        .join(Game, Season)\
                        .filter(cls.player==player, 
                                Game.game_type==game_type, 
                                Season.year==season)\
                        .one()
                        
    @classmethod
    def team_season(cls, team, season_year):
        return DBSession.query(cls)\
                        .with_polymorphic('*')\
                        .join(Game, Season)\
                        .filter(Season.year==season_year,
                                cls.team==team)
                                
class FootballPassingStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    attempts = Column(Integer)
    completions = Column(Integer)
    yards = Column(Integer)
    touchdowns = Column(Integer)
    interceptions = Column(Integer)
    sacks = Column(Integer)
    sack_yards = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'passing'}
      
    @classmethod
    def abbr(cls):
        return [
                (cls.attempts,  'att'),
                (cls.completions, 'comp'),
                (cls.yards, 'yd'),
                (cls.touchdowns, 'td'),
                (cls.interceptions, 'int'),
                (cls.sacks,'sk'),
                (cls.sack_yards, 'sk_yd')
            ]
            
    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]
    
    @classmethod
    def sum_q(cls):
        return 'yd'
            
    @classmethod
    def full_cats(cls):
        c = [(k.name, v) for k, v in cls.abbr()]
        c.insert(3, ('yards per attempt', 'y/a'))
        c.insert(3, ('yards per completion', 'y/c'))
        c.insert(2, ('completion percent', 'c%'))
        c.append(('yards per game', 'y/g'))
        return c
        
    @classmethod
    def calc_additional(cls, players):
        p_list = []
        for p in players:
            p = p._asdict()
            stats = []
            for cat, abbr in cls.full_cats():
                if abbr in p:
                    s = p[abbr]
                elif abbr == 'y/g':
                    s = round(float(p['yd'])/p['gp'], 1)
                elif abbr == 'c%':
                    s = round(float(p['att'])/p['comp']*100, 2)
                elif abbr == 'y/c':
                    s = round(float(p['yd'])/p['comp'], 1)
                elif abbr == 'y/a':
                    s = round(float(p['yd'])/p['att'], 1)
                stats.append(s)
            p['stats'] = stats
            p_list.append(p)
        players = sorted(p_list, key=lambda x: x['stats'][-1], reverse=True)
        return players

class FootballRushingStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    attempts = Column(Integer)
    yards = Column(Integer)
    touchdowns = Column(Integer)
    longest = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'rushing'}
    
    @classmethod
    def abbr(cls):
        return [
                (cls.attempts,  'att'),
                (cls.yards, 'yd'),
                (cls.touchdowns, 'td'),
                (cls.longest, 'long'),
            ]
                
    @classmethod
    def sum_query(cls):
        s_q = cls.abbr()[:-1]
        s_q = [func.sum(k).label(v) for k, v in s_q]
        s_q.append(func.max(cls.longest).label('long'))
        return s_q
        
    @classmethod
    def sum_q(cls):
        return 'yd'
    
class FootballReceivingStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    receptions = Column(Integer)
    yards = Column(Integer)
    touchdowns = Column(Integer)
    longest = Column(Integer)
    targets = Column(Integer)

    __mapper_args__ = {'polymorphic_identity': 'receiving'}

    @classmethod
    def abbr(cls):
        return [
            (cls.receptions, 'rec'),
            (cls.yards, 'yd'),
            (cls.touchdowns, 'td'),
            (cls.targets, 'tgt'),
            (cls.longest, 'long'),
        ]
        
    @classmethod
    def sum_query(cls):
        s_q = cls.abbr()[:-1]
        s_q = [func.sum(k).label(v) for k, v in s_q]
        s_q.append(func.max(cls.longest).label('long'))
        return s_q

    @classmethod
    def sum_q(cls):
        return 'yd'
    
class FootballFumbleStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    fumbles = Column(Integer)
    recovered = Column(Integer)
    lost = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'fumble'}
   
    @classmethod
    def abbr(cls):
        return [
            (cls.fumbles, 'tot'),
            (cls.recovered, 'rec'),
            (cls.lost, 'lost')
        ]

    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]
        
    @classmethod
    def sum_q(cls):
        return 'lost'

class FootballDefensiveStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    tackles = Column(Integer)
    solo = Column(Integer)
    sacks = Column(Integer)
    tackles_for_loss = Column(Integer)
    pass_deflections = Column(Integer)
    qb_hits = Column(Integer)
    touchdowns = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'defensive'}

    @classmethod
    def abbr(cls):
        return [
            (cls.tackles, 'tkl'),
            (cls.solo, 'solo'),
            (cls.sacks, 'sk'),
            (cls.tackles_for_loss, 'tfl'),
            (cls.pass_deflections, 'pd'),
            (cls.qb_hits, 'hits'),
            (cls.touchdowns, 'td'),
        ]
                
    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]
    
    @classmethod
    def sum_q(cls):
        return 'tkl'
    
class FootballReturnStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    total = Column(Integer)
    yards = Column(Integer)
    longest = Column(Integer)
    touchdowns = Column(Integer)
    return_type = Column(String)
    
    __mapper_args__ = {'polymorphic_identity': 'return'}
    
    @classmethod
    def abbr(cls):
        return [
            (cls.total, 'tot'),
            (cls.yards, 'yd'),
            (cls.touchdowns, 'td'),
            (cls.longest, 'long'),
        ]
                
    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]   
        
    @classmethod
    def sum_q(cls): 
        return 'tot'       

class FootballKickingStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    fg_made = Column(Integer)
    fg_attempts = Column(Integer)
    longest = Column(Integer)
    xp_made = Column(Integer)
    xp_attempts = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'kicking'}
    
    @classmethod
    def abbr(cls):
        return [
            (cls.fg_made, 'fgm'),
            (cls.fg_attempts, 'fga'),
            (cls.xp_made, 'xpm'),
            (cls.xp_attempts, 'xpa')
        ]
                
    @classmethod
    def sum_query(cls):
        s_q = [func.sum(k).label(v) for k, v in cls.abbr()]
        s_q.append(func.max(cls.longest).label('long'))
        return s_q
        
    @classmethod
    def sum_q(cls):
        return 'xpa'
        
    @classmethod
    def full_cats(cls):
        fc = cls.abbr()
        fc.append((cls.longest, 'long'))
        return [(k.name\
                  .replace('fg', 'field goals')\
                  .replace('xp', 'extra points')\
                  .replace('_', ' '), v) for k, v in fc]

    @classmethod
    def calc_additional(cls, players, stat_type):
        p_list = []
        cats = cls.full_cats()
        for p in players:
            p = p._asdict()
            p['stats'] = [p[abbr] for k, abbr in cats]
            p_list.append(p)
        players = sorted(p_list, key=lambda x: x['fgm'], reverse=True)
        return players, cats

class FootballPuntingStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    total = Column(Integer)
    yards = Column(Integer)
    touchbacks = Column(Integer)
    inside_20 = Column(Integer)
    longest = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'punting'}
    
    @classmethod
    def abbr(cls):
        return [
            (cls.total, 'tot'),
            (cls.yards, 'yd'),
            (cls.touchbacks, 'tb'),
            (cls.inside_20, 'i20')
        ]
                
    @classmethod
    def sum_query(cls):
        s_q = [func.sum(k).label(v) for k, v in cls.abbr()]
        s_q.append(func.max(cls.longest).label('long'))
        return s_q
        
    @classmethod
    def sum_q(cls):
        return 'tot'
    
    @classmethod
    def full_cats(cls):
        fc = cls.abbr()
        fc.append((cls.longest, 'long'))
        return [(k.name.replace('_', ' '), v) 
                    for k, v in fc]

    @classmethod
    def calc_additional(cls, players, stat_type):
        p_list = []
        cats = cls.full_cats()
        for p in players:
            p = p._asdict()
            p['stats'] = [p[abbr] for k, abbr in cats]
            p_list.append(p)
        players = sorted(p_list, key=lambda x: x['tot'], reverse=True)
        return players, cats

class FootballInterceptionStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    total = Column(Integer)
    yards = Column(Integer)
    touchdowns = Column(Integer)
     
    __mapper_args__ = {'polymorphic_identity': 'interception'}

    @classmethod
    def abbr(cls):
        return [
            (cls.total, 'tot'),
            (cls.yards, 'yd'),
            (cls.touchdowns, 'td')
        ]
                
    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]
        
    @classmethod
    def sum_q(cls):
        return 'tot'
        
class FootballOffensiveStat(PlayerStat):
    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    passing_attempts = Column(Integer)
    passing_completions = Column(Integer)
    passing_yards = Column(Integer)
    passing_touchdowns = Column(Integer)
    passing_interceptions = Column(Integer)
    passing_sacks = Column(Integer)
    passing_sack_yards = Column(Integer)
    rushing_attempts = Column(Integer)
    rushing_yards = Column(Integer)
    rushing_touchdowns = Column(Integer)
    rushing_longest = Column(Integer)
    receiving_receptions = Column(Integer)
    receiving_yards = Column(Integer)
    receiving_touchdowns = Column(Integer)
    receiving_longest = Column(Integer)
    receiving_targets = Column(Integer)
    fumble_fumbles = Column(Integer)
    fumble_recovered = Column(Integer)
    fumble_lost = Column(Integer)
    punt_return_total = Column(Integer)
    punt_return_yards = Column(Integer)
    punt_return_longest = Column(Integer)
    punt_return_touchdowns = Column(Integer)
    kick_return_total = Column(Integer)
    kick_return_yards = Column(Integer)
    kick_return_longest = Column(Integer)
    kick_return_touchdowns = Column(Integer)
    
    __mapper_args__ = {'polymorphic_identity': 'offense'}
                
    @classmethod
    def abbr(cls, stat_type):
        a_dict = {
            'passing':[
                (cls.passing_completions, 'pass_comp'),
                (cls.passing_attempts, 'pass_att'),
                (cls.passing_yards, 'pass_yd'),
                (cls.passing_sacks, 'pass_sk'),
                (cls.passing_sack_yards, 'pass_sk_yd'),
                (cls.passing_interceptions, 'pass_int'),
                (cls.passing_touchdowns, 'pass_td')
            ],
            'rushing': [
                (cls.rushing_attempts, 'rush_att'),
                (cls.rushing_yards, 'rush_yd'),
                (cls.rushing_touchdowns, 'rush_td'),
            ],
            'receiving': [
                (cls.receiving_receptions, 'rec_rec'),
                (cls.receiving_targets, 'rec_tgt'),
                (cls.receiving_yards, 'rec_yd'),
                (cls.receiving_touchdowns, 'rec_td')
            ],
            'return': [
                (cls.kick_return_total, 'kick_ret_tot'),
                (cls.kick_return_yards, 'kick_ret_yd'),
                (cls.kick_return_touchdowns, 'kick_ret_td'),
                (cls.punt_return_total, 'punt_ret_tot'),
                (cls.punt_return_yards, 'punt_ret_yd'),
                (cls.punt_return_touchdowns, 'punt_ret_td'),
            ],
            'fumbles': [
                (cls.fumble_fumbles, 'fum_tot'),
                (cls.fumble_lost, 'fum_lost'),
            ]
        }
        a = a_dict[stat_type]
        if stat_type in ['passing', 'rushing', 'receiving']:
            a += a_dict['fumbles']
        return a
    
    @classmethod
    def sum_query(cls, stat_type):
        sum_query = [func.sum(k).label(v) for k, v in cls.abbr(stat_type)]
        if stat_type == 'return':
            q = 'ret_tot'
            add = cls.kick_return_total+cls.punt_return_total
            sum_query.append(func.sum(add).label('ret_tot'))
        else:
            q = '%s_yd' % stat_type.replace('ing', '').replace('eiv', '')
        return q, sum_query
        
    @classmethod
    def full_cats(cls, stat_type):
        c = [(k.name, v) for k, v in cls.abbr(stat_type)]
        if stat_type == 'passing':
            c.insert(3, ('yards per attempt', 'y/a'))
            c.insert(3, ('yards per completion', 'y/c'))
            c.insert(2, ('completion percent', 'c%'))
            c.append(('yards per game', 'y/g'))
        elif stat_type == 'rushing':
            c.insert(2, ('yards per attempt', 'y/a'))
            c.append(('yards per game', 'y/g'))
        elif stat_type == 'receiving':
            c.insert(2, ('targets per game', 't/g'))
            c.insert(2, ('receptions per game', 'r/g'))
            c.insert(2, ('yards per reception', 'y/r'))
            c.append(('yards per game', 'y/g'))
        return c
        
    @classmethod
    def calc_additional(cls, players, stat_type):
        full_cats = cls.full_cats(stat_type)
        p_list = []
        for p in players:
            p = p._asdict()
            stats = []
            for cat, abbr in full_cats:
                if abbr in p:
                    s = p[abbr]
                elif stat_type == 'passing':
                    if abbr == 'y/g':
                        s = round(float(p['pass_yd'])/p['gp'], 1)
                    elif abbr == 'c%':
                        s = round(float(p['pass_att'])/p['pass_comp']*100, 2)
                    elif abbr == 'y/c':
                        s = round(float(p['pass_yd'])/p['pass_comp'], 1)
                    elif abbr == 'y/a':
                        s = round(float(p['pass_yd'])/p['pass_att'], 1)
                elif stat_type == 'rushing':
                    if abbr == 'y/g':
                        s = round(float(p['rush_yd'])/p['gp'], 1)
                    elif abbr == 'y/a':
                        s = round(float(p['rush_yd'])/p['rush_att'], 1)
                elif stat_type == 'receiving':
                    if abbr == 'y/g':
                        s = round(float(p['rec_yd'])/p['gp'], 1)
                    elif abbr == 'y/r':
                        s = round(float(p['rec_yd'])/p['rec_rec'], 1)
                    elif abbr == 't/g':
                        s = round(float(p['rec_tgt'])/p['gp'], 1)
                    elif abbr == 'r/g':
                        s = round(float(p['rec_rec'])/p['gp'], 1)
                stats.append(s)
            p['stats'] = stats
            p_list.append(p)
        players = sorted(p_list, key=lambda x: x['stats'][-1], reverse=True)
        return players, full_cats
                
class FootballDefenseSpecialTeamsStat(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    yards_allowed = Column(Integer)
    sack_total = Column(Integer)
    sack_yards = Column(Integer)
    fumbles_forced = Column(Integer)
    fumbles_recovered = Column(Integer)
    interceptions = Column(Integer)
    points_allowed = Column(Integer)
    touchdowns = Column(Integer)
    safeties = Column(Integer)
                
class FootballTeamStat(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    passing_first_downs = Column(Integer)
    rushing_first_downs = Column(Integer)
    penalty_first_downs = Column(Integer)
    third_down_attempts = Column(Integer)
    third_down_conversions = Column(Integer)
    fourth_down_attempts = Column(Integer)
    fourth_down_conversions = Column(Integer)
    plays = Column(Integer)
    yards = Column(Integer)
    drives = Column(Integer)
    passing_yards = Column(Integer)
    passing_attempts = Column(Integer)
    passing_completions = Column(Integer)
    interceptions = Column(Integer)
    sack_total = Column(Integer)
    sack_yards = Column(Integer)
    rushing_yards = Column(Integer)
    rushing_attempts = Column(Integer)
    red_zone_attempts = Column(Integer)
    red_zone_conversions = Column(Integer)
    penalty_total = Column(Integer)
    penalty_yards = Column(Integer)
    fumbles_lost = Column(Integer)
    defensive_special_teams_tds = Column(Integer)
    time_of_possession = Column(Time)
    
    game = relationship('Game', backref=(backref('team_stats')))
    team = relationship('Team')
    
    @classmethod
    def sum_query(cls):
        
        sum_query = [
            func.count(cls.sack_total).label('sacks'),
            func.count(cls.defensive_special_teams_tds).label('td'),
            func.count(cls.interceptions).label('interceptions'),
        ]
        return sum_query
        
    @classmethod
    def headers(cls):
       return ['passing_first_downs', 'rushing_first_downs', 
               'penalty_first_downs', 'third_down_attempts', 
               'third_down_conversions', 'fourth_down_attempts', 
               'fourth_down_conversions', 'plays', 'yards', 'drives', 
               'passing_yards', 'passing_attempts', 'passing_completions', 
               'interceptions', 'sack_total', 'sack_yards', 'rushing_yards', 
               'rushing_attempts', 'red_zone_attempts', 'red_zone_conversions', 
               'penalty_total', 'penalty_yards','fumbles_lost', 
               'defensive_special_teams_tds']
    
class BasketballMixin(object):    
    minutes = Column(Integer)     
    field_goals_made = Column(Integer)
    field_goals_attempted = Column(Integer)
    threes_made = Column(Integer)
    threes_attempted = Column(Integer)
    free_throws_made = Column(Integer)
    free_throws_attempted = Column(Integer)
    offensive_rebounds = Column(Integer)
    defensive_rebounds = Column(Integer)
    rebounds = Column(Integer)
    assists = Column(Integer)
    steals = Column(Integer)
    blocks = Column(Integer)
    turnovers = Column(Integer)
    personal_fouls = Column(Integer)
    plus_minus = Column(Integer)
    points = Column(Integer)
    
    def per_game(self, stat):
        if stat:
            per_game = round(float(stat)/self.games_played, 2)
        else:
            return 0
        return per_game
    
    def per_36(self, stat):
        if stat:
            per_36 = round(float(stat)/self.minutes*36, 2)
        else:
            return 0
        return per_36
    
    def free_throw_pct(self):
        if self.free_throws_made:
            ft_pct = round(float(self.free_throws_made)/float(self.free_throws_attempted)*100, 2)
        else:
            return 0
        return ft_pct
        
    def field_goal_pct(self):
        if self.field_goals_attempted:
            fg_pct = round(float(self.field_goals_made)/float(self.field_goals_attempted)*100, 2)
        else:
            return 0
        return fg_pct
        
    def threes_pct(self):
        if self.threes_attempted:
            threes_pct = round(float(self.threes_made)/float(self.threes_attempted)*100, 2)
        else:
            return 0
        return threes_pct
    
    def two_pt_fg_made(self):
        return self.field_goals_made - self.threes_made
    
    def two_pt_fg_attempted(self):
        return self.two_pt_fg_attempted - self.two_pt_fg_attempted
        
    def two_pt_fg_pct(self):
        return round(float(self.two_pt_fg_made())/float(self.two_pt_fg_attempted())*100, 2)
        
    def ts(self):
        ts = round(self.points/(2*self.field_goals_attempted + 0.44*stat.free_throws_attempted)*100, 2)
        
    def efg(self):
        efg = round((self.field_goals_made + 0.5 * self.threes_made)/self.field_goals_attempted*100, 2)
        return efg
        
    def credits(self):
        credits = (self.points + self.rebounds + self.steals + 
                    self.blocks - self.field_goals_missed - 
                    self.free_throws_missed - self.turnovers)
    
    def approximate_value(self):
        av = round((float(self.credits)*3/4)/21, 2)
        return av
        
    def assist_pct(self):
        return ''
        '''
        assist_pct = 100*self.assists/(((self.minutes
        100*Assists/(((Minutes Played /(Team Minutes/5)) * Team Field Goals Made) - Field Goals Made)
        '''

class BasketballBoxScoreStat(BasketballMixin, PlayerStat):

    id = Column(Integer, ForeignKey('player_stat.id'), primary_key=True)
    
    '''
    player_stat = relationship('PlayerStat', 
                            backref=backref('basketball_stat', uselist=False))
    '''
    
    __mapper_args__ = {'polymorphic_identity': 'box_score'}
    
    @classmethod
    def abbr(cls):
        return [
            (cls.minutes, 'min'),
            (cls.field_goals_made, 'fgm'),
            (cls.field_goals_attempted, 'fga'),
            (cls.threes_made, '3ptm'),
            (cls.threes_attempted, '3pta'),
            (cls.free_throws_made, 'ftm'),
            (cls.free_throws_attempted, 'fta'),
            (cls.offensive_rebounds, 'oreb'),
            (cls.defensive_rebounds, 'dreb'),
            (cls.rebounds, 'reb'),
            (cls.assists, 'ast'),
            (cls.steals, 'stl'),
            (cls.blocks, 'blk'),
            (cls.turnovers, 'tos'),
            (cls.personal_fouls, 'pf'),
            (cls.plus_minus, '+/-'),
            (cls.points, 'pts')
        ]
        
    @classmethod
    def full_cats(cls):
        c = [(k.name, v) for k, v in cls.abbr()]
        c.insert(3, ('field goal percent', 'fg%'))
        c.insert(6, ('three point percent', '3pt%'))
        c.insert(9, ('free throw percent', 'ft%'))
        return c
    
    @classmethod
    def sum_query(cls):
        return [func.sum(k).label(v) for k, v in cls.abbr()]
    
    @classmethod
    def calc_add(cls, players, stat_type):
        p_list = []
        for p in players:
            p = p._asdict()
            stats = []
            for cat, abbr in cls.full_cats():
                if abbr in ['fg%', 'ft%', '3pt%']:
                    base = abbr[:-1]
                    try:
                        s = round(float(p[base+'m'])/p[base+'a'] * 100, 2)
                    except ZeroDivisionError:
                        s = 0
                elif abbr == 'gp':
                    s = ['gp']
                elif stat_type == 'game':
                    s = round(float(p[abbr])/p['gp'], 1)
                elif stat_type == '36':
                    if abbr == 'min':
                        s = p['min']
                    else:
                        try:
                            s = round(float(p[abbr])*36/p['min'], 1)
                        except ZeroDivisionError:
                            s = 0
                else:
                    s = p[abbr]
                stats.append(s)
            p['stats'] = stats
            p_list.append(p)
        players = p_list
        return sorted(p_list, key= lambda x: x['stats'][-1], reverse=True)
    
    def __repr__(self):
        return '%s' % self.player.person
        
class BasketballSeasonStat(BasketballMixin, Base):
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    season_id = Column(Integer, ForeignKey('season.id'))
    games_played = Column(Integer)
    game_type = Column(String)
    
    __mapper_args__ = {'polymorphic_identity': 'box_score'}
    
    player = relationship('Player')
    team = relationship('Team')
    season = relationship('Season')
    
    def __repr__(self):
        return '%s' % self.player.person
    
    
class BasketballTeamStat(Base):
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('game.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    field_goals_made = Column(Integer)
    field_goals_attempted = Column(Integer)
    threes_made = Column(Integer)
    threes_attempted = Column(Integer)
    free_throws_made = Column(Integer)
    free_throws_attempted = Column(Integer)
    offensive_rebounds = Column(Integer)
    defensive_rebounds = Column(Integer)
    rebounds = Column(Integer)
    assists = Column(Integer)
    steals = Column(Integer)
    blocks = Column(Integer)
    turnovers = Column(Integer)
    personal_fouls = Column(Integer)
    points = Column(Integer)
    paint_points = Column(Integer)
    fast_break_points = Column(Integer)
    points_off_turnover = Column(Integer)
    
    team = relationship('Team', uselist=False)
    game = relationship('Game', uselist=False)
    

    
