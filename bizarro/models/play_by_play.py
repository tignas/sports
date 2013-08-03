from meta import *

class Play(Base):
    id = Column(Integer, primary_key=True)
    play_number = Column(Integer)
    game_id = Column(Integer, ForeignKey('game.id'))
    source_name = Column(String, ForeignKey('source.name'))
    home_score = Column(Integer)
    away_score = Column(Integer)
    period = Column(Integer)
    time_of_game = Column(Time)
    full_description = Column(Text)
    event_type = Column(String)
    
    game = relationship('Game', uselist=False)    

    __mapper_args__ = {'polymorphic_on': event_type}

    def __repr__(self):
        return '%s %s' % (self.event_type, self.full_description)
    
    def score(self):
        return '(%s-%s)' % (self.away_score, self.home_score)
        
    def period_string(self):
        periods = {
        1: '1st',
        2: '2nd',
        3: '3rd',
        4: '4th',
        }
        return periods[self.period]

class Shot(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    shooter_id = Column(Integer, ForeignKey('player.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    length = Column(Integer)
    shot_type = Column(String)
    points = Column(Integer)
    make = Column(Boolean)
    adjective = Column(String)
    
    team = relationship('Team', uselist=False)
    shooter = relationship('Player', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity': 'shot'}
    
    def made(self):
        if self.make:
            return 'makes'
        else:
            return 'misses'

class Block(Shot):
    id = Column(Integer, ForeignKey('shot.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'))
    blocker_id = Column(Integer, ForeignKey('player.id'))
    
    blocker = relationship('Player', uselist=False, lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity':'block'}

class Assist(Shot):    
    id = Column(Integer, ForeignKey('shot.id'), primary_key=True)
    assistant_id = Column(Integer, ForeignKey('player.id'))
    
    assistant = relationship('Player', uselist=False, lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity':'assist'}
    
class ShotCoordinates(Base):
    id = Column(Integer, primary_key=True)
    shot_id = Column(Integer, ForeignKey('shot.id'))
    external_shot_id = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)
    length = Column(Integer)
    shot_type = Column(String)
    
    shot = relationship('Shot', 
                        backref=backref('shot_coordinates', lazy='joined', 
                                        uselist=False),
                        lazy='joined', uselist=False)
    
class Rebound(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    shot_id = Column(Integer, ForeignKey('shot.id'))	
    team_id = Column(Integer, ForeignKey('team.id'))
    offensive = Column(Boolean)

    team = relationship('Team', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity':'rebound'}

class PlayerRebound(Rebound):
    id = Column(Integer, ForeignKey('rebound.id'), primary_key=True)
    rebounder_id = Column(Integer, ForeignKey('person.id'))
    
    rebounder = relationship('Person', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity':'player_rebound'}	

class Clock(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    action = Column(String)
    
    __mapper_args__ = {'polymorphic_identity': 'clock'}

class Timeout(Clock):
    id = Column(Integer, ForeignKey('clock.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'))
    timeout_type = Column(String)
    
    team = relationship('Team', uselist=False, lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity': 'timeout'}

class PlayerTimeout(Timeout):
    id = Column(Integer, ForeignKey('timeout.id'), primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    
    player = relationship('Player', uselist=False, lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity': 'player_timeout'}

class Ejection(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team')
    player = relationship('Player', uselist=False, lazy='joined')
    
    __mapper_args__ = {'polymorphic_identity': 'ejection'}

class Jumpball(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    winner_id = Column(Integer, ForeignKey('player.id'))
    loser_id = Column(Integer, ForeignKey('player.id'))
    possession_team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team', uselist=False)    
    winner = relationship('Player', uselist=False, 
                          primaryjoin="Jumpball.winner_id == Player.id")
    loser = relationship('Player', uselist=False, 
                         primaryjoin="Jumpball.loser_id == Player.id")
    
    __mapper_args__ = {'polymorphic_identity': 'jumpball'}

class PlayerJumpball(Jumpball):
    id = Column(Integer, ForeignKey('jumpball.id'), primary_key=True)	
    possessor_id = Column(Integer, ForeignKey('player.id'))
    
    possessor = relationship('Player', primaryjoin='PlayerJumpball.possessor_id'
                             '== Player.id', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity': 'player_jumpball'}

class Substitution(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    player_in_id = Column(Integer, ForeignKey('player.id'))
    player_out_id = Column(Integer, ForeignKey('player.id'))
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team')
    player_in = relationship('Player', primaryjoin='Substitution.player_in_id =='
                             'Player.id', uselist=False)
    player_out = relationship('Player', primaryjoin='Substitution.player_out_id' 
                              '== Player.id', uselist=False)
    
    __mapper_args__ = {'polymorphic_identity': 'substitution'}

class Foul(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    foul_type = Column(String)
    description = Column(Text)
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team')

    __mapper_args__ = {'polymorphic_identity': 'foul'}
    
class CoachFoul(Foul):
    id = Column(Integer, ForeignKey('foul.id'), primary_key=True)
    commiter_id = Column(Integer, ForeignKey('coach.id'))

    commiter = relationship('Coach', 
                        primaryjoin='CoachFoul.commiter_id==Coach.id')
    
    __mapper_args__ = {'polymorphic_identity': 'coach_foul'}
    
class PlayerFoul(Foul):
    id = Column(Integer, ForeignKey('foul.id'), primary_key=True)
    commiter_id = Column(Integer, ForeignKey('player.id'))

    commiter = relationship('Player', 
                        primaryjoin='PlayerFoul.commiter_id==Player.id')
    
    __mapper_args__ = {'polymorphic_identity': 'player_foul'}

class DrawFoul(PlayerFoul):    
    id = Column(Integer, ForeignKey('player_foul.id'), primary_key=True)
    drawer_id = Column(Integer, ForeignKey('player.id'))
    
    drawer = relationship('Player', 
                          primaryjoin ='DrawFoul.drawer_id==Player.id', 
                          uselist=False)
    
    __mapper_args__ = {'polymorphic_identity': 'draw_foul'}

class Violation(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    violation_type = Column(String)
    result = Column(String)
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team')
    
    __mapper_args__ = {'polymorphic_identity': 'violation'}

class PlayerViolation(Violation):
    id = Column(Integer, ForeignKey('violation.id'), primary_key=True)
    violator_id = Column(Integer, ForeignKey('player.id'))
    
    violator = relationship('Player')

    __mapper_args__ = {'polymorphic_identity': 'player_violation'}

class Steal(Play):
    id = Column(Integer, ForeignKey('play.id'), primary_key=True)
    stealer_id = Column(Integer, ForeignKey('player.id'))
    turnerover_id = Column(Integer, ForeignKey('player.id'))
    steal_type = Column(String)
    result = Column(String)
    team_id = Column(Integer, ForeignKey('team.id'))
    
    team = relationship('Team')
    stealer = relationship('Player', uselist=False,
                            primaryjoin='Steal.stealer_id == Player.id')
    turnerover = relationship('Player', uselist=False, 
                                primaryjoin='Steal.turnerover_id == Player.id')
    
    __mapper_args__ = {'polymorphic_identity': 'steal'}
