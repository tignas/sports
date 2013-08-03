from meta import *

class Network(Base):
    abbr = Column(String, primary_key=True)
    name = Column(String)
    website = Column(String)
    
    def __repr__(self):
        return '%s' % self.abbr

class Twitter(Base):
    id = Column(Integer, primary_key=True)
    handle = Column(String)
    name = Column(String)
    created = Column(DateTime)
    tag = Column(String)
    person_id = Column(Integer, ForeignKey('person.id'))
    source_name = Column(String, ForeignKey('source.name'))
    
    person = relationship('Person', uselist=False)
    source = relationship('Source', uselist=False)
    leagues = relationship('League', secondary='twitter_league')
    teams = relationship('Team', secondary='twitter_team')

    def __repr__(self):
        return '%s @%s' % (self.name, self.handle)
    
class TwitterLeague(Base):
    twitter_id = Column(Integer, ForeignKey('twitter.id'), primary_key=True)
    league_id = Column(Integer, ForeignKey('league.id'), primary_key=True)
    
class TwitterTeam(Base):
    twitter_id = Column(Integer, ForeignKey('twitter.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)
    
class Source(Base):
    name = Column(String, primary_key=True)
    full_name = Column(String)
    url = Column(String)
    source_type = Column(String)
    
    def __repr__(self):
        return '%s %s' % (self.name, self.url)

class FeedTeam(Base):
    feed_id = Column(Integer, ForeignKey('rss_feed.id'), primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), primary_key=True)

class FeedPlayer(Base):
    feed_id = Column(Integer, ForeignKey('rss_feed.id'), primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), primary_key=True)
    
class FeedLeague(Base):
    feed_id = Column(Integer, ForeignKey('rss_feed.id'), primary_key=True)
    league_id = Column(Integer, ForeignKey('league.id'), primary_key=True)

class FeedWriter(Base):
    feed_id = Column(Integer, ForeignKey('rss_feed.id'), primary_key=True)
    writer_id = Column(Integer, ForeignKey('writer.id'), primary_key=True)

class FeedSport(Base):
    feed_id = Column(Integer, ForeignKey('rss_feed.id'), primary_key=True)
    sport_name = Column(String, ForeignKey('sport.name'), primary_key=True)
    
class RSSFeed(Base):
    id = Column(Integer, primary_key=True)
    url = Column(String)
    source_name = Column(String, ForeignKey('source.name'))
    feed_type = Column(String)
    sub_type = Column(String)
    last_update = Column(DateTime)
    
    teams = relationship('Team', secondary='feed_team')
    players = relationship('Player', secondary='feed_player')
    leagues = relationship('League', secondary='feed_league')
    sports = relationship('Sport', secondary='feed_sport')
    writers = relationship('Writer', secondary='feed_writer')
    
    def __repr__(self):
        return '%s feed %s %s' % (self.feed_type, self.source_name, self.url)

class Writer(Base):
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'))
    
    person = relationship('Person', uselist=False, lazy='joined')
    
    sources = relationship('Source', secondary='writer_source')
    
    def __repr__(self):
        return '%s' % self.person        
    
class WriterSource(DateMixin, Base):
    writer_id = Column(Integer, ForeignKey('writer.id'), primary_key=True)
    source_name = Column(Integer, ForeignKey('source.name'), primary_key=True)
    
class MediaItem(Base):
    id = Column(Integer, primary_key=True)
    source_name = Column(String, ForeignKey('source.name'))
    url = Column(String)
    title = Column(String)
    summary = Column(Text)
    published = Column(DateTime)
    updated = Column(DateTime)
    media_type = Column(String)
    
    league = relationship('League', secondary='media_item_league', 
                            uselist=False)
    __mapper_args__ = {'polymorphic_on': media_type}
    
    source = relationship(Source)
   
    
class Article(MediaItem):
    id = Column(Integer, ForeignKey('media_item.id'), primary_key=True)
    writer_id = Column(Integer, ForeignKey('writer.id'))
    #at some point change this to writer_id
    
    writer = relationship('Writer')
    
    __mapper_args__ = {'polymorphic_identity': 'article'}
    
class Video(MediaItem):
    id = Column(Integer, ForeignKey('media_item.id'), primary_key=True)
    length = Column(Time)
    video_type = Column(String)
    
    __mapper_args__ = {'polymorphic_identity': 'video'}
    
class MediaItemLeague(Base):
    media_item_id = Column(Integer, ForeignKey('media_item.id'), primary_key=True)
    league_id = Column(Integer, ForeignKey('league.id'), primary_key=True)
    
class Keywords(Base):
    media_item_id = Column(Integer, ForeignKey('media_item.id'), primary_key=True)
    keyword = Column(String, primary_key=True)
    

