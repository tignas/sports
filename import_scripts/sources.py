# -*- coding: utf-8 -*-
from connect_db import *
from bizarro.models.media import *
from bizarro.models.people import *
from bizarro.models.teams import *
from datetime import datetime
from time import mktime
import feedparser
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from pprint import pprint
import urllib2, urllib
import json
import re
from bizarro.api.media import *

sources = [
    {
        'full_name': 'sports illustrated',
        'name': 'si',
        'url': 'http://sportsillustrated.cnn.com/',
    },
    {
        'full_name': 'entertainment and sports programming network',
        'name': 'espn',
        'url': 'http://espn.go.com/',
    },
    {
        'full_name': 'national basketball association',
        'name': 'league',
        'url': 'http://www.nba.com/',
    },
    {
        'full_name': 'hoopsworld',
        'name': 'hoopsworld',
        'url': 'http://www.hoopsworld.com/',
    },
    {
        'full_name': 'rotoworld',
        'name': 'rotoworld',
        'url': 'http://www.rotoworld.com/',
    },
    {
        'full_name': 'columbia broadcasting system',
        'name': 'cbs',
        'url': 'http://cbssports.com/',
    },
    {
        'full_name': 'fox',
        'name': 'fox',
        'url': 'http://msn.foxsports.com/',
    },
    {
        'full_name': 'usa today',
        'name': 'usa today',
        'url': 'http://www.usatoday.com/sports/'
    },
    {
        'full_name': 'draft express',
        'name': 'draftexpress',
        'url': 'http://www.usatoday.com/sports/'
    },
    {
        'full_name': 'nba stuffer',
        'name': 'nba stuffer',
        'url': 'http://www.nbastuffer.com/'
    },
    {
        'full_name': 'national football league',
        'name': 'nfl',
        'url': 'http://www.nfl.com/'
    },
    {
        'full_name': 'FFtoolbox',
        'name': 'fftoolbox',
        'url': 'http://www.fftoolbox.com'
    },
]

def create_sources():
    session = create_session()
    for source in sources:
        source, created = get_or_create(session, Source,
                                        **source)
  
feeds = [
    {'source_name': 'si',
     'url': 'http://rss.cnn.com/rss/si_nba.rss',
     'feed_type': 'league',
     'league': 'nba'},    
    {'source_name': 'espn',
     'url': 'http://sports.espn.go.com/espn/rss/nba/news',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'hoopsworld',
     'url': 'http://www.hoopsworld.com/category/nba/feed/',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'rotoworld',
     'url': 'http://www.rotoworld.com/rss/feed.aspx?' + \
            'sport=nba&ftype=news&count=12&format=rss',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'rotoworld',
     'url': 'http://www.rotoworld.com/rss/feed.aspx?' + \
            'sport=nba&ftype=article&count=12&format=rss',
     'feed_type': 'league',
     'league': 'nba'}, 
    {'source_name': 'usa today',
     'url': 'http://content.usatoday.com/marketing/rss/' + \
            'rsstrans.aspx?feedId=sports5',
     'feed_type': 'league',
     'league': 'nba'},
    {'source_name': 'fox',
     'url': 'http://edge1.catalog.video.msn.com/videoByTag.aspx?tag=Fox%' + \
            '20Sports_NBA20news&ns=MSNVideo_Top_Cat&mk=us&sd=-1&sf=' + \
            'ActiveStartDate&vs=0&ind=&ps=&rct=&ff=88&responseEncoding' + \
            '=rss&title=FOX%20Sports%20Video%20on%20MSN:%' + \
            '20NBA&template=foxsports&p=foxsports',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'cbs',
     'url': 'http://cbssports.com/partners/feeds/rss/nba_news',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'cbs',
     'url': 'http://cbssports.com/partners/feeds/rss/nbaplayerupdates',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'draftexpress',
     'url': 'http://www.nba.com/rss/nba_rss.xml',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'nba stuffer',
     'url': 'http://feeds.feedburner.com/NbastufferBlog',
     'feed_type': 'league',
     'league': 'nba'},   
    {'source_name': 'nba stuffer',
     'url': 'http://feeds.feedburner.com/NbaPlayerMovements',
     'feed_type': 'league',
     'league': 'nba'},
]

ff_feeds = [
    {'source_name': 'rotoworld',
    'url': 'http://www.rotoworld.com/rss/feed.aspx?sport=nfl&count=12&format=rss&ftype=news',
    'feed_type': 'news',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'rotoworld',
    'url': 'http://www.rotoworld.com/rss/feed.aspx?sport=nfl&count=12&format=rss&ftype=article',
    'feed_type': 'articles',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/football_fantasy_news',
    'feed_type': 'news',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/nflplayerupdates',
    'feed_type': 'player',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/nfl_news',
    'feed_type': 'news',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/ClarkJudge_columns',
    'feed_type': 'writer',
    'league': 'nfl',},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/JameEisenberg_columns',
    'feed_type': 'writer',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/PetePrisco_columns',
    'feed_type': 'writer',
    'league': 'nfl'},
    {'source_name': 'cbs',
    'url': 'http://cbssports.com/partners/feeds/rss/DaveRichard_columns',
    'feed_type': 'writer',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'nfl',
    'url': 'http://www.nfl.com/rss/rsslanding?searchString=team&abbr=%s',
    'feed_type': 'news',
    'league': 'nfl'},
    {'source_name': 'fftoolbox',
    'url': 'http://feeds.feedburner.com/FFToolboxFantasyFootballUpdates',
    'feed_type': 'updates',
    'sub_type': 'fantasy',
    'league': 'nfl'},
    {'source_name': 'fftoolbox',
    'url': 'http://feeds.feedburner.com/NFL_News_and_Rumors',
    'feed_type': 'news',
    'league': 'nfl'},
    {'source_name': 'fftoolbox',
    'url': 'http://feeds.feedburner.com/FFToolboxNFLDraft',
    'feed_type': 'news',
    'sub_type': 'draft',
    'league': 'nfl'},
    {'source_name': 'fftoolbox',
    'url': 'http://www.blogtalkradio.com/fftoolbox.rss',
    'feed_type': 'podcast',
    'sub_type': 'fantasy',
    'league': 'nfl'}
]

def create_feed(session, source, league, f):
    feed, c = get_or_create(session, RSSFeed, **f)
    feed.leagues.append(league)
    session.commit()
    if f['feed_type'] == 'writer':
        if f['source_name'] == 'cbs':
            writer_name = f['url'].rpartition('/')[2].split('_')[0]
            writer_name = re.sub(r'(\w)([A-Z])', r'\1 \2', writer_name)
        writer = get_or_create_writer(session, writer_name, source)
        if not writer in feed.writers:
            feed.writers.append(writer)
            session.commit()
    return feed

def create_feeds():    
    session = create_session()
    for f in ff_feeds:
        league_abbr = f.pop('league')
        league = session.query(League)\
                        .filter_by(abbr=league_abbr)\
                        .one()
        source = session.query(Source)\
                        .filter(Source.name==f['source_name'])\
                        .one()
        if f['source_name'] == 'nfl':
            teams = session.query(Team).filter(Team.league==league)
            base = f.pop('url')
            for team in teams:
                url = base % team.abbr
                f.update({'url': url})
                feed = create_feed(session, source, league, f)
                feed.teams.append(team)
        else:
            create_feed(session, source, league, f)
    session.commit()
            
def import_videos():
    session = create_session()
    base_url = 'http://gdata.youtube.com/feeds/api/videos?author=%s&v=2&alt=json'
    channels = ['nba', 'nbaonespn']
    for channel in channels[0:1]:
        url = base_url % channel
        f = urllib2.urlopen(url)
        results = json.loads(f.read())
        print results['feed']['entry'][0]['link']#.keys()
        

def import_feeds():
    session = create_session()
    feeds = session.query(RSSFeed).all()
    for feed in feeds:
        print feed
        f = feedparser.parse(feed.url)
        for entry in f['entries']:
            if entry.has_key('published_parsed'):
                published = datetime.fromtimestamp(mktime(entry['published_parsed']))                
            if entry.has_key('updated_parsed'):
                updated = datetime.fromtimestamp(mktime(entry['updated_parsed']))
            else:
                updated = published
            title = entry['title']
            link = entry['link']
            article_args = {
                'source_name': feed.source_name,
                'url': link,
                'title': title
            }
            article, created = get_or_create(session, Article, **article_args)
            article.published = published
            article.updated = updated
            save(session, article)
    
def import_twitters(league_abbr):
    session = create_session()
    league = session.query(League).filter(League.abbr==league_abbr).one()
    if league.abbr == 'nba':
        '''
        league = '@NBA / @NBAPR / @NBAOfficial / @NBA_Labor / @NBAHistory / @NBAAllStar / @NBAJamSession / @NBAStore / @nbacares / @NBAStats / @Ene_Be_A / @NBAUK / @NBAMEX / @TheNBPA '
        league_handles = league.split(' / ')
        for handle in league_handles:
            source_name = 'nba'
            lt, created = get_or_create(session, Twitter,
                                        handle=handle[1:],
                                        source_name=source_name)
        writers = """Adrian Wojnaroski / Yahoo! / @WojYahooNBA
Chris Sheridan / SheridanHoops.com / @SheridanHoops
Ian Thomsen / SI.com / @SI_IanThomsen 
Chris Mannix / SI.com / @ChrisMannixSI
Sam Amick / USA Today / @sam_amick
Zach Lowe / Grantland.com / @ZachLowe_NBA
Howard Beck / New York Times / @HowardBeckNYT
Jonathan Abrams / Grantland / @jpdabrams
Ken Berger / CBSSports.com / @KBergCBS
Marc J. Spears / Yahoo! / @SpearsNBAHoops
Josh Robbins / Orlando Sentinel / @JoshuaBRobbins
Brian Mahoney / Associated Press / @briancmahoney
Sean Deveney / The Sporting News / @SeanDeveney
Peter Vecsey / New York Post / @PeterVecsey1
Michael Lee / Washington Post / @MrMichaelLee
Eddie Sefko / Dallas Morning News / @Esefko
Scott Soshnick / Bloomberg News / @soshnick 
Steve Luhm / Salt Lake Tribune / @sluhm
Jeff Zillgitt / USA Today / @usat_jzillgitt
J. Michael Falgoust / USA Today / @jmikeNBAusat
Gary Washburn / Boston Globe / @gwashburn14
Mark Murphy / Boston Herald / @Murf56
Shaun Powell / Sports on Earth / @Powell2daPeople"""
        writer_handles = writers.split('\n')
        for handle in writer_handles:
            writer_name, source_name, handle = handle.split(' / ')
            writer_query = session.query(Writer)\
                                  .join(Person, PersonName)\
                                  .filter(PersonName.full_name==writer_name)
            try:
                writer = writer_query.one()
            except MultipleResultsFound:
                for a in writer_query.all()[1:]:
                    session.delete(a)
            try:
                source = session.query(Source)\
                                .filter(Source.full_name==source_name).one()
            except NoResultFound:
                source = Source(full_name=source_name, name=source_name)
                session.add(source)
                session.commit() 
            ws = get_or_create(session, WriterSource, writer_id=writer.id, 
                               source_name=source_name)
            twitter_info = {
                'handle': handle[1:],
                'name': writer_name,
                'source_name': source_name,
                'person_id': writer.person.id,                                
            }
            twitter, created = get_or_create(session, Twitter, **twitter_info)
            lt = get_or_create(session, TwitterLeague, 
                               twitter_id=twitter.id, league_id=league.id)
        writers = """Chris Broussard / @Chris_Broussard
Marc Stein / @ESPNSteinLine
Chad Ford / @ChadFordInsider
Brian Windhorst / @windhorstespn
J.A. Adande / @jadande
Henry Abbott / @TrueHoop
Kevin Arnovitz / @KevinArnovitz
John Hollinger / @JohnHollinger
Chris Palmer / @ESPNChrisPalmer
Tom Haberstroh / @TomHaberstroh
David Thorpe / @coachthorpe
Michael Wilbon / @RealMikeWilbon
Larry Coon / @LarryCoon
Israel Gutierrez / @IzzyESPN 
Royce Webb / @RoyceWebb 
Jordan Brenner / @JordanBrenner"""
        writer_handles = writers.split('\n')
        source_name = 'espn'
        source = session.query(Source).filter_by(name=source_name).one()
        for handle in writer_handles:
            writer_name, handle = handle.split(' / ')
            writer_query = session.query(Writer)\
                                  .join(Person, PersonName)\
                                  .filter(PersonName.full_name==writer_name)
            
            try:
                writer = writer_query.one()
            except MultipleResultsFound:
                for a in writer_query.all()[1:]:
                    session.delete(a) 
                    session.commit()
            except NoResultFound:
                print writer_name
                raise Exception('hello')   
            print writer         
            ws = get_or_create(session, WriterSource, writer_id=writer.id, 
                               source_name=source_name)
            twitter_info = {
                'handle': handle[1:],
                'name': writer_name,
                'source_name': source_name,
                'person_id': writer.person.id,                                
            }
            twitter, created = get_or_create(session, Twitter, **twitter_info)
            lt = get_or_create(session, TwitterLeague, 
                               twitter_id=twitter.id, league_id=league.id)
        writers = """Scott Howard-Cooper / @SHowardCooper
David Aldridge / @daldridgetnt
Steve Aschburner / @AschNBA
John Schuhmann / @johnschuhmann
Sekou Smith / @SekouSmithNBA 
Fran Blinebury / @FranBlinebury
Jeff Caplan / @Caplan_NBA
Drew Packham / @drewpackham"""
        source_name = 'nba'
        source = session.query(Source).filter_by(name=source_name).one()
        writer_handles = writers.split('\n')
        for handle in writer_handles:
            writer_name, handle = handle.split(' / ')
            writer_query = session.query(Writer)\
                                  .join(Person, PersonName)\
                                  .filter(PersonName.full_name==writer_name)
            try:
                writer = writer_query.one()
            except MultipleResultsFound:
                for a in writer_query.all()[1:]:
                    session.delete(a) 
                    session.commit()
            except NoResultFound:
                pprint(writer_name)
                raise Exception('hello')
            print writer         
            ws = get_or_create(session, WriterSource, writer_id=writer.id, 
                               source_name=source_name)
            twitter_info = {
                'handle': handle[1:],
                'name': writer_name,
                'source_name': source_name,
                'person_id': writer.person.id,                                
            }
            twitter, created = get_or_create(session, Twitter, **twitter_info)
            lt = get_or_create(session, TwitterLeague, 
                               twitter_id=twitter.id, league_id=league.id)
        writers = """Rick Kamla / @NBATVRick
Dennis Scott / @3Deezy
Steve Smith / @Steve21Smith
Greg Anthony / @GregAnthony50
Cheryl Miller / @NBATVCheryl
Chris Webber / @RealChrisWebber
Matt Winer / @Matt_Winer
Vince Cellini / @Vince_Cellini
Jared Greenberg / @NBATVJared """
        source_name = 'nba tv'
        source = session.query(Source).filter_by(name=source_name).one()
        writer_handles = writers.split('\n')
        for handle in writer_handles:
            writer_name, handle = handle.split(' / ')
            writer_query = session.query(Writer)\
                                  .join(Person, PersonName)\
                                  .filter(PersonName.full_name==writer_name)
            try:
                writer = writer_query.one()
            except MultipleResultsFound:
                for a in writer_query.all()[1:]:
                    session.delete(a) 
                    session.commit()
            except NoResultFound:
                pprint(writer_name)
                raise Exception('hello')
            print writer         
            ws = get_or_create(session, WriterSource, writer_id=writer.id, 
                               source_name=source_name)
            twitter_info = {
                'handle': handle[1:],
                'name': writer_name,
                'source_name': source_name,
                'person_id': writer.person.id,                                
            }
            twitter, created = get_or_create(session, Twitter, **twitter_info)
            lt = get_or_create(session, TwitterLeague, 
                               twitter_id=twitter.id, league_id=league.id)
        writers = """Ernie Johnson / @TurnerSportsEJ
Kenny Smith / @TheJetOnTNT
Reggie Miller / @ReggieMillerTNT 
Craig Sager / @TNT_CraigSager
Mike Fratello / @MikeFratello
Cheryl Miller / @NBATVCheryl """
        source_name = 'tnt'
        source = session.query(Source).filter_by(name=source_name).one()
        writer_handles = writers.split('\n')
        for handle in writer_handles:
            writer_name, handle = handle.split(' / ')
            writer_query = session.query(Writer)\
                                  .join(Person, PersonName)\
                                  .filter(PersonName.full_name==writer_name)
            try:
                writer = writer_query.one()
            except MultipleResultsFound:
                for a in writer_query.all()[1:]:
                    session.delete(a) 
                    session.commit()
            except NoResultFound:
                pprint(writer_name)
                raise Exception('hello')
            print writer         
            ws = get_or_create(session, WriterSource, writer_id=writer.id, 
                               source_name=source_name)
            twitter_info = {
                'handle': handle[1:],
                'name': writer_name,
                'source_name': source_name,
                'person_id': writer.person.id,                                
            }
            twitter, created = get_or_create(session, Twitter, **twitter_info)
            lt = get_or_create(session, TwitterLeague, 
                               twitter_id=twitter.id, league_id=league.id)
        blogs = u"""ESPN TrueHoop: @TrueHoop / @TrueHoopTV / @TrueHoopNetwork
HoopsHype: @hoopshype 
InsideHoops.com: @insidehoops
SheridanHoops.com: @SheridanBlog / @MarkHeisler / @Whyhub / @JB_For_3_ / @ChrisBernucca / @ChrisPerk / @SheridanHoopsFantasy
Hoopsworld: @hoopsworld / @SteveKylerNBA / @AlexKennedyNBA / @EricPincus @TommyBeer / @AlexRaskinNYC / @LangGreene / @TheRocketGuy / @JFlemingHoops / @DPageHoopsWorld / @stevesraptors / @SusanBible / @joelbrigham / @DrTravisHeath / @YannisHW
NBC Pro Basketball Talk: @basketballtalk / @KurtHelin / @BrettEP / @Rotoworld_BK / @Docktora / @AaronBruski / @AdamLevitan / @fosterdj
CBS Eye on Basketball: @EyeOnBasketball / @MattMooreCBS / @talkhoops / @dailythunder
New York Times Off the Dribble: @HowardBeckNYT / @ByNateTaylor / @JPCavan / @zinsernyt / @KnickerBlogger / @BobSaietta
Yahoo! Ball Dont Lie: @KDonHoops / @YourManDevine / @freemaneric
Grantland: @sportsguy33 / @ZachLowe_NBA / @jpdabrams
SB Nation: @SBNationNBA / @teamziller / @MikePradaSBN / @andrewsharp
The Basketball Jones: @jeskeets / @tasmelas / @TreyKerby / @BallerMindFrame / @ScottCarefoot / @AUgetoffmygold / @MarkDeeksNBA / @graydongordian 
Hardwood Paroxysm: @HPBasketball
RealGM: @RealGM
Hoops Rumors: @HoopsRumors  
NBA Info Daily: @NBAInfoDaily
The Breakdown Show: @BreakdownShow / @DaveMendonca / @theaudman
Hoops Addict: @ryanmcneill
The Hoop Doctors: @anklesnap 
Shaky Ankles: @ShakyAnkles 
The No Look Pass: @TheNoLookPass 
About.com NBA: @charliezegers 
Hardcourt Mayhem: @JoshDhani / @insidethearc
Digital Sports Desk: @terrylyon 
The Chase Down Block: @Mark_Travis / @jakin1013 
The Sports Network: @JFMcMullen
NBAtipoff: @NBAtipoff"""
        blog_handles = blogs.split('\n')
        for handle in blog_handles:
            source_name, handles = handle.split(': ')
            source = session.query(Source)\
                            .filter(Source.full_name==source_name)\
                            .first()
            if not source:
                source = Source(full_name=source_name, name=source_name)
            source.source_type = 'blog'
            session.add(source)
            session.commit()
            handles = handles.split(' / ')
            for handle in handles:
                twitter = session.query(Twitter)\
                                 .filter(Twitter.handle==handle).all()
                if not twitter:
                    twitter = Twitter(handle=handle[1:], 
                                      source_name=source_name)
                    session.add(twitter)
                    session.commit()
                lt = get_or_create(session, TwitterLeague, 
                                   twitter_id=twitter.id, 
                                   league_id=league.id)
        mags = """SLAMonline: @SLAMonline / @bosborne17 / @LangWhitaker / @slaman10 / @susaningrid21 / @afigman / @marcel_mutoni / @TTwersky / @JakeAppleman / @FrankieC7 / @RussBengtson / @mdotbrown / @San_Dova / @abe_squad 
DimeMag.com: @DimeMag / @SEANesweeney / @AndrewGreif / @DimeJosh / @PatrickECassidy
HoopMag.com: @HoopMag"""        
        mag_handles = mags.split('\n')
        for handle in mag_handles:
            source_name, handles = handle.split(': ')
            source = session.query(Source)\
                            .filter(Source.full_name==source_name)\
                            .first()
            if not source:
                source = Source(full_name=source_name, name=source_name)
            source.source_type = 'magazine'
            session.add(source)
            session.commit()
            handles = handles.split(' / ')
            for handle in handles:
                twitter = session.query(Twitter)\
                                 .filter(Twitter.handle==handle).all()
                if not twitter:
                    twitter = Twitter(handle=handle[1:], 
                                      source_name=source_name)
                    session.add(twitter)
                    session.commit()
                lt = get_or_create(session, TwitterLeague, 
                                   twitter_id=twitter.id, 
                                   league_id=league.id)
        stats = """Basketball Prospectus: @bballprospectus / @kpelton / @bbdoolittle / @Sportsref_Neil
Hoopdata: @hoopdata 
Basketball Reference: @bball_ref
BasketballValue.com: @basketballvalue
Popcorn Machine: @pmgameflows
The Wages of Wins Journal: @nerdnumbers / @arturogalletti
Hickory-High: @HickoryHigh"""
        stat_handles = stats.split('\n')
        for handle in stat_handles:
            source_name, handles = handle.split(': ')
            source = session.query(Source)\
                            .filter(Source.full_name==source_name)\
                            .first()
            if not source:
                source = Source(full_name=source_name, name=source_name)
            source.source_type = 'website'
            session.add(source)
            session.commit()
            handles = handles.split(' / ')
            for handle in handles:
                twitter = session.query(Twitter)\
                                 .filter(Twitter.handle==handle).all()
                if not twitter:
                    twitter = Twitter(handle=handle[1:], 
                                      source_name=source_name)
                    session.add(twitter)
                    session.commit()
                lt = get_or_create(session, TwitterLeague, 
                                   twitter_id=twitter.id, 
                                   league_id=league.id)
        drafts = """Draft Express: @DraftExpress
NBADraft.net: @nbadraftnet
NBA Draft Blog: @nbadraftblog
Swish Scout: @swishscout"""
        draft_handles = drafts.split('\n')
        for handle in draft_handles:
            source_name, handles = handle.split(': ')
            source = session.query(Source)\
                            .filter(Source.full_name==source_name)\
                            .first()
            if not source:
                source = Source(full_name=source_name, name=source_name)
            source.source_type = 'draft website'
            session.add(source)
            session.commit()
            handles = handles.split(' / ')
            for handle in handles:
                twitter = session.query(Twitter)\
                                 .filter(Twitter.handle==handle).all()
                if not twitter:
                    twitter = Twitter(handle=handle[1:], 
                                      source_name=source_name)
                    session.add(twitter)
                    session.commit()
                lt = get_or_create(session, TwitterLeague, 
                                   twitter_id=twitter.id, 
                                   league_id=league.id)
        drafts = """Sign and Trade: @SignAndTrade
Rotoworld: @Rotoworld_BK / @docktora / @aaronbruski / @Knaus_RW / @adamlevitan / @MikeSGallagher / @Mr_Norof
Baller Mind Frame: @aka_MR_FANTASY
NetScouts Basketball: @NetScouts / @chrisdenker / @carlberman
Tommy Dee: @TommyDeeTKB
Sports Law 101: @sportslaw101
Hoopism: @hoopisms
HoopSpeak: @HoopSpeak / @beckleymason / @SherwoodStrauss / @outsidethenba
In All Airness: @inallairness"""
        draft_handles = drafts.split('\n')
        for handle in draft_handles:
            source_name, handles = handle.split(': ')
            source = session.query(Source)\
                            .filter(Source.full_name==source_name)\
                            .first()
            if not source:
                source = Source(full_name=source_name, name=source_name)
            source.source_type = 'website'
            session.add(source)
            session.commit()
            handles = handles.split(' / ')
            for handle in handles:
                twitter = session.query(Twitter)\
                                 .filter(Twitter.handle==handle).all()
                if not twitter:
                    twitter = Twitter(handle=handle[1:], 
                                      source_name=source_name)
                    session.add(twitter)
                    session.commit()
                lt = get_or_create(session, TwitterLeague, 
                                   twitter_id=twitter.id, 
                                   league_id=league.id)
        '''
        teams = [
            {
            'name':'hawks',
            'team_twitter': "Atlanta Hawks / @ATLHawks",
            'writers': """Michael Cunningham / Atlanta Journal Constitution / @ajchawks
Chris Vivlamore / Atlanta Journal Constitution / @ajchawks""",
            'blogs': """Peachtree Hoops / @peachtreehoops
Soaring Down South / @WillSevidalSDS
Hoopinion / @hoopinion
Hawk Squawk / @TheHawkSquawk""",
            'players': """Al Horford / @Al_Horford
John Jenkins / @JohnnyCashVU23
Dahntay Jones / @dahntay1
Kyle Korver / @KyleKorver
Zaza Pachulia / @zaza27
Johan Petro / @Frenchi27
DeShawn Stevenson / @Dsteve92JMarie 
Jeff Teague / @Teague0
Anthony Tolliver / @ATolliver44
Jeremy Tyler / @jeremytyler3
Louis Williams / @TeamLou23""",
            'arena': "Philips Arena / @PhilipsArena",
            'mascot': "Harry the Hawk / @HARRY_THE_HAWK"
            },
            {
            'name':'celtics',
            'team_twitter': "Boston Celtics / @celtics",
            'writers': """Frank Dell'Appa / Boston Globe / @frankdellappa 
Gary Washburn / Boston Globe / @gwashburn14
Gary Dzen / Boston Globe / @globegarydzen
Mark Murphy / Boston Herald / @murphmj
Dan Duggan / Boston Herald / @dduggan
Scott Souza / Metro West Daily News / @scott_souza
A. Sherrod Blakely / Comcast Sportsnet / @SherrodbCSN
Jessica Camerato / Comcase Sportsnet  / @JCameratoNBA
Chris Forsberg / ESPN Boston / @ESPNForsberg
Paul Flannery / WEEI.com / @pflanns""",
            'blogs': """Celtics Hub / @CelticsHub
Celtics 24/7 / @Celtics_247
Celtics Blog / @CelticsBlog
Red's Army / @RedsArmy_John""",
            'players': """Avery Bradley / @Avery_Bradley
Jordan Crawford / @jcraw55
Jeff Green / @unclejeffgreen
Courtney Lee / @CourtneyLee2211
Fab Melo / @Fabpmelo
Paul Pierce / @PaulPierce34
Rajon Rondo / @rajonrondo
Jared Sullinger / @Jared_Sully0
Jason Terry / @jasonterry31
Chris Wilcox / @ChrisWilcox44
Terrence Williams / @TheRealTWill""",
            },
            {
            'name':'nets',
            'team_twitter': "Brooklyn Nets / @BrooklynNets",
            'writers': """Howard Beck / New York Times / @HowardBeckNYT 
Stefan Bondy / New York Daily News / @NYDNInterNets
Tim Bontemps / New York Post / @TimBontemps 
Roderick Boone / Newsday / @rodboone
Andy Vasquez / Bergen Record / @andy_vasquez
Colin Stephenson / The Star-Ledger / @colinledger
Fred Kerber / New York Post / @NYPost_Nets
Mike Mazzeo / ESPN New York / @MazzESPN
Josh Newman / SportsNet New York / @Joshua_Newman 
Ben Couch / NBA.com/Nets / @viewfromcouch
Moke Hamilton / SNY.tv / @MokeHamilton""",
            'blogs': """Nets are Scorching / @NetsRScorching
Brooklyn Bound / @Bound4Brooklyn
Nets Daily / @NetsDaily""",
            'players': """Andray Blatche / @drayblatche
MarShon Brooks / @Marshon2
Reggie Evans / @ReggieEvans30
Kris Humphries / @KrisHumphries
Joe Johnson / @TheJoeJohnson7
Tornike Shengelia / @TokoShengelia23
Jerry Stackhouse / @jerrystackhouse
Tyshawn Taylor / @tyshawntaylor
Mirza Teletovic / @MirzaTeletovic
C.J. Watson / @quietstorm_32
Deron Williams / @DeronWilliams""",
            'arena': "Barclays Center / @barclayscenter",
            'execs': """Brett Yormark / CEO / @brettyormark
Billy King / GM / @bkdefend
Gary Sussman / VP of PR / @sussez
Nets PR / @Nets_PR"""
            },
            {
            'name':'bobcats',
            'team_twitter': "Charlotte Bobcats  / @bobcats",
            'writers': """Rick Bonnell / Charlotte Observer / @rick_bonnell
Richard Walker / Gaston Gazette / @JRWalk22 
Steve Reed / AP / @SteveReedAP""",
            'blogs': """Queen City Hoops / 
Rufus on Fire / @CardboardGerald
Bobcats Planet / @bobcatsplanet
Bobcats Baseline / @bobcatsbaseline
Roberto Gato / @therobertogato""",
            'players': """Jeff Adrien / @Adrien4
Bismack Biyombo / @bismackbiyombo0
DeSagana Diop / @sagana7
Ben Gordon / @BenGordon8
Gerald Henderson / @GhJr09
Michael Kidd-Gilchrist / @MikeGillie14
Byron Mullens / @byron22james
Ramon Sessions / @SessionsRamon
Tyrus Thomas / @tyrusthomas
Kemba Walker / @KembaWalker
Reggie Williams / @reggiew55""",
            'arena': "Time Warner Cable Arena / @TWCArena",
            'mascot': "Rufus Lynx / @rufuslynx",
            'execs': """B.J. Evans / Director of Communications / @BobcatsBballPR""",
            },
            {
            'name':'bulls',
            'team_twitter': "Chicago Bulls / @chicagobulls",
            'writers': """K.C. Johnson / Chicago Tribune / @KCJHoop
Neil Hayes / Chicago Sun-Times / @bynhayes
Mike McGraw / Daily Herald / @McGrawDHBulls
Nick Friedell / ESPN Chicago / @ESPNChiBulls 
Sam Smith / Bulls.com Blog / @SamSmithHoops
Aggrey Sam / CSN Chicago / @CSNBullsInsider""",
            'blogs': """Blog-A-Bull / @BullsBlogger
Pippen Ain't Easy / @PippenAintEasy_
Chicago Bulls Confidential / @dougthonus 
Bulls Podcasters / @TheBullsShow 
Chi City Sports / @ChiCitySports23
Da Bulls' Eye / @dabullseye
Bulls 101 / @Bulls_101
DaBullz.com / @dabullz""",
            'players': """Marco Belinelli / @marcobelinelli 
Carlos Boozer / @MisterCBooz
Jimmy Butler / @mr_2eight1
Daequan Cook / @DC4three
Luol Deng / @LuolDeng9
Taj Gibson / @TajGibson22
Richard Hamilton / @ripcityhamilton
Nazr Mohammed / @NazrMuhammed
Joakim Noah / @JoakimNoah
Nate Robinson / @nate_robinson
Derrick Rose / @drose
Marquis Teague / @marquisteague25""",
            'arena': "United Center / @unitedcenter",
            'mascot': "Benny the Bull / @bennythebull",
            'execs': """Bull PR / @ChicagoBulls_PR"""
            },
            {
            'name':'cavaliers',
            'team_twitter': "Cleveland Cavaliers / @cavs",
            'writers': """Mary Schmitt Boyer / The Plain Dealer / @pdcavsinsider
Bob Finnan / The News-Herald / @BobCavsInsider
Jason Lloyd / Akron Beacon Journal / @JasonLloydABJ
Tom Withers / AP / @twithersap""",
            'blogs': """Waiting for Next Year / @WFNYScott / @WFNYCraig / @RockWFNY / @RickWFNY
Cavs: The Blog / @johnkrolik
Fear the Sword / @FearTheSword
Right Down Euclid / @KJG_CodyN
Stepien Rules / @ChrisGrantland""",
            'players': """Omri Casspi / @casspi18
Wayne Ellington / @WayneElli22
Alonzo Gee / @GeeAlonzo 
Daniel Gibson / @BooBysWorld1
Kyrie Irving / @KyrieIrving
Kevin Jones / @kevjones5
C.J. Miles / @masfresco
Josh Selby / @JoshSelby2
Marreese Speights / @mospeights16
Tristan Thompson / @RealTrist13
Dion Waiters / @dionwaiters3
Tyler Zeller / @ZellerTyler""",
            'arena': "Quicken Loans Areana / @TheQGirls",
            'mascot': "Sir CC / @CavsSirCC",
            'execs': """Dan Gilbert / Owner / @cavsdan"""
            },
            {
            'name':'mavericks',
            'team_twitter': "Dallas Mavericks / @dallasmavs",
            'writers': """Eddie Sefko / Dallas Morning News / @ESefko
Brad Townsend / Dallas Morning News / @townbrad
Dwain Price / Star-Telegram / @DwainPrice
Tim MacMahon / ESPN Dallas / @espn_macmahon
Earl K. Sneed / Mavs.com / @EKS_mavsnba """,
            'blogs': """DallasBasketball.com / @fishsports 
The Two Man Game / @robmahoney
Mavs Moneyball / @mavsmoneyball 
The Smoking Cuban / @thesmokingcuban""",
            'players': """Rodrigue Beaubois / @RoddyBeaubois3
Elton Brand / @EltonBrand2
Vince Carter / @mrvincecarter15
Darren Collison / @Darren_Collison
Jae Crowder / @CJC9BOSS
Jared Cunningham / @J1Flight
Bernard James / @iBall_
Mike James / @mikejames7
Dominique Jones / @Dojo20
Chris Kaman / @ChrisKaman
Shawn Marion / @matrix31
O.J. Mayo / @juicemayo32
Anthony Morrow / @MrAnthonyMorrow  
Dirk Nowitzki / @swish41
Brandan Wright / @bwright34""",
            'mascot': """Champ / @MavsChamp
Mavs Man / @OfficialMavsMan""",
            'execs': """Mark Cuban / Owner / @mcuban"""
            },
            {
            'name':'nuggets',
            'team_twitter': "Denver Nuggets / @denvernuggets",
            'writers': """Benjamin Hochman / The Denver Post / @nuggetsnews
Chris Dempsey / The Denver Post / @dempseypost
Aaron Lopez / Nuggets.com / @Lopez_Nuggets """,
            'blogs': """Denver Stiffs / @denverstiffs
Roundball Mining Company / @RoundballMiner""",
            'players': """Corey Brewer / @CoreyBrewer13
Wilson Chandler / @wilsonchandler
Kenneth Faried / @KennethFaried35
Evan Fournier / @EvanFourmizz
Danilo Gallinari / @gallinari8888
Jordan Hamilton / @J_Goin_Ham
Andre Iguodala / @MindofAI9
Kosta Koufos / @kostakoufos
Ty Lawson / @tylawson3
JaVale McGee / @JaValeMcGee34
Quincy Miller / @qmillertime
Timofey Mozgov / @TimofeyMozgov
Anthony Randolph / @TheARandolph
Julyan Stone / @J_Stone5""",
            'arena': "Pepsi Center / @Pepsi_Center",
            'mascot': """Rocky the Lion / @RockyTheLion""",
            },
            {
            'name':'pistons',
            'team_twitter': "Detroit Pistons / @detroitpistons",
            'writers': """Dave Mayo / MLIVE Media Group / @David_Mayo
Dave Pemberton / Oakland Journal - Pistons' Point / @drpemberton
Brendan Savage / Flint Journal / @BrendanSavage
Vincent Goodwill / Detroit News / @vgoodwill
Vince Ellis / Detroit Free Press / @VinceEllis56""",
            'blogs': """Piston Powered / @pistonpowered / @patrick_hayes
Need 4 Sheed / @need4sheed_com
Detroit Bad Boys / @detroitbadboys
True Blue Pistons / @Keith_Langlois
Pistons by the Numbers / @brgulker""",
            'players': """Will Bynum / @WillBynum12
Jose Calderon / @josemcalderon8
Andre Drummond / @DRE_DRUMMOND_
Kim English / @Englishscope24
Jonas Jerebko / @JonasJerebko
Brandon Knight / @BrandonKnight12
Slava Kravtsov / @SlavaKravstov
Corey Maggette / @ghostC5M
Jason Maxiell / @JasonMaxiell
Khris Middleton / @Khris22m
Greg Monroe / @G_Monroe10
Kyle Singler / @KyleSingler
Rodney Stuckey / @RodneyStuckey3
Charlie Villanueva / @CV31""",
            'arena': "The Palace / @ThePalace",
            'execs': """Tom Gores / Owner / @TomGores""",
            },
            {
            'name':'warriors',
            'team_twitter': "Golden State Warriors / @warriors",
            'writers': """Rusty Simmons / San Francisco Chronicle / @Rusty_SFChron
Marcus Thompson / Mercury News / @gswscribe
Matt Steinmetz / Comcast Bay Area / @MSteinmetzCSN""",
            'blogs': """Warriors World / @warriorsworld / @SherwoodStrauss
Golden State of Mind / @unstoppablebaby
Fast Break: Warriors Fan Blog / @GSWFastBreak""",
            'players': """Harrison Barnes / @HBarnes
Kent Bazemore / @kentbazmore20
Stephen Curry / @stephencurry30
Festus Ezeli / @fezzyfel
Draymond Green / @Money23Green
Jarrett Jack / @JarrettJack03
Carl Landry / @CarlLandry
David Lee / @DLee042
Brandon Rush / @KCsFinest4""",
            'arena': "Oracle Arena / @OracleArenaAEG",
            'execs': """Peter Guber / Owner / @PeterGuber
Mark Jackson / Head Coach / @JacksonMark13
Dan Martinez / PR Director / @dmar""",
            },
            {
            'name':'rockets',
            'team_twitter': "Houston Rockets / @Rockets",
            'writers': """Jonathan Feigen / Houston Chronicle / @Jonathan_Feigen
Jason Friedman / Rockets.com / @RocketsJCF 
Terrance Harris / CBS Houston / @TerranceHarris 
MK Bower / Fox Sports Houston / @moisekapenda""",
            'blogs': """The Dream Shake / @DreamShakeSBN
Clutch Fans / @ClutchFans
Red94 / @RedNinetyFour / @ShakyAnkles
Hoopsworld / @TheRocketGuy""",
            'players': """James Anderson / @JA_Five
Omer Asik / @OmerAsik
Patrick Beverley / @patbev21
Carlos Delfino / @cabezadelfino
Francisco Garcia / @cisco32
James Harden / @JHarden13 
Tyler Honeycutt / @thoneycutt23
Terrence Jones / @TerrenceJones1
Jeremy Lin / @JLin7
Chandler Parsons / @ChandlerParsons
Thomas Robinson / @Trobinson0
Royce White / @Highway_30""",
            'arena': "Toyota Center / @ToyotaCenterTix",
            'execs': """Daryl Morey / GM / @dmorey""",
            'mascot': "Clutch the Bear / @clutchthebear"
            },
            {
            'name':'pacers',
            'team_twitter': "Indiana Pacers / @Pacers",
            'writers': """Mike Wells / Indy Star / @MikeWellsNBA
Mike Marot / AP / @apmarot 
Scott Agness / Pacers.com / @ScottAgness""",
            'blogs': """Indy Cornrows / @indycornrows
Eight Points, Nine Seconds / @8pts9secs""",
            'players': """Paul George / @King24George
Danny Granger / @dgranger33
Ben Hansbrough / @bhans23
Tyler Hansbrough / @THANS50
Roy Hibbert / @Hoya2aPacer
George Hill / @George_Hill3
Orlando Johnson / @Pace_O11
Ian Mahinmi / @Ianmahinmi
Jeff Pendergraph / @TheRealJP31
Miles Plumlee / @milesplumlee13
Lance Stephenson / @StephensonLance
David West / @D_West30
Sam Young / @SamYoung4""",
            'arena': "Bankers Life Fieldhouse / @TheFieldHouse",
            'execs': """David Benner / Director of Media Relations / @PacersDMB
Krissy Myers / Media Relations Rep / @PacersKrissy""",
            'mascot': "Boomer / @PacersBoomer"
            },
            {
            'name':'clippers',
            'team_twitter': "L.A. Clippers / @LAClippers",
            'writers': """Broderick Turner / L.A. Times / @BA_Turner
Beth Harris / AP / @bethharrisap 
Dan Woike / Orange County Register / @DanWoikeSports""",
            'blogs': """ClipperBlog / @clipperblog
Clips Nation / @clippersteve""",
            'players': """Matt Barnes / @Matt_Barnes22
Caron Butler / @realtuffjuice
Jamal Crawford / @JCrossover
Willie Green / @WillieGreen33RO
Blake Griffin / @blakegriffin
Grant Hill / @realgranthill33
Ryan Hollins / @TheRyanHollins
DeAndre Jordan / @deandrejordan
Lamar Odom / @reallamarodom
Chris Paul / @CP3
Trey Thompkins / @TreyThompkins
Ronny Turiaf / @Ronny_Turiaf""",
            'arena': "Staples Center / @STAPLESCenterLA",
            },
            {
            'name':'lakers',
            'team_twitter': "L.A. Lakers / @lakers",
            'writers': """Kevin Ding / The Orange County Register / @KevinDing
Janis Carr / The Orange County Register / @janiscarr
Mike Bresnahan / L.A. Times / @Mike_Bresnahan
Elliot Teaford / Daily Breeze / @ElliotTeaford
Dave McMenamin / ESPNLA.com / @mcten
Brian and Andy Kamenetzky / ESPNLA.com / @ESPNLandOLakers
Mike Trudell / Lakers.com Blog / @LakersReporter""",
            'blogs': """Lakers Nation / @LakersNation
Silver Screen and Roll / @LakersBlog_SSR
Round-the-Clock Purple and Gold / @Latmedina
Forum Blue and Gold / @forumbluegold
The Purple and Gold Blog / @TPGBlog
Laker Nation / @LakerNation
With Malice / @withmalice
Lake Show Life / @lakeshowlife
Laker Liker / @LakerLiker""",
            'players': """Steve Blake / @SteveBlake5
Kobe Bryant / @kobebryant
Earl Clark / @3eazy
Chris Duhon / @CDuhonStandTall
Devin Ebanks / @DevinEbanks3
Pau Gasol / @paugasol
Jordan Hill / @jordanchill43
Dwight Howard / @DwightHoward
Antawn Jamison / @Antawn_Jamison4
Jodie Meeks / @jmeeks20
Darius Morris / @dariusmorris4
Steve Nash / @SteveNash
Robert Sacre / @Lakers_Sacre50
Metta World Peace / @MettaWorldPeace""",
            'arena': "Staples Center / @STAPLESCenterLA",
            'execs': """Jeanie Buss / EVP / @JeanieBuss""",
            },
            {
            'name':'grizzlies',
            'team_twitter': "Memphis Grizzlies / @memgrizz",
            'writers': """Chris Herrington  / Memphis Flyer / @FlyerGrizzBlog
Ronald Tillery / Commercial Appeal / @CAGrizzBlog""",
            'blogs': """3 Shades of Blue / @3sob 
Straight Outta Vancouver / @sbnGrizzlies""",
            'players': """Tony Allen / @aa000G9
Jerryd Bayless / @jerrydbayless
Mike Conley / @mconley11
Ed Davis / @eddavis32
Austin Daye / @Adaye5
Marc Gasol / @MarcGasol
Jon Leuer / @JLeu30
Dexter Pittman / @DexPittmanreal
Quincy Pondexter / @quincypondexter
Tayshaun Prince / @tay_prince
Zach Randolph / @MacBo50
Tony Wroten / @TWroten_LOE""",
            'arena': "FedEx Forum / @FedExForum",
            'mascot': """Grizz / @grizz""",
            },
            {
            'name':'heat',
            'team_twitter': "Miami Heat / @MiamiHEAT",
            'writers': """Tim Reynolds / AP / @ByTimReynolds 
Ethan J. Skolnick / Palm Beach Post / @EthanJSkolnick
 Tom Haberstroh / ESPNs Heat Index / @tomhaberstroh
Michael Wallace / ESPN's Heat Index / @WallaceNBA_ESPN
Brian Windhorst / ESPN's Heat Index / @WindhorstESPN
Joseph Goodman / Miami Herald / @MiamiHeraldHeat
Ira Winderman / Sun Sentinel / @IraHeatBeat
Shandel Richardson / Sun Sentinel / @ShandelRich
 Chris Tomassen / Fox Sports Florida / @ChrisTomasson""",
            'blogs': """Hot Hot Hoops / @HotHotHoops / @SuryaHeatNBA
Peninsula is Mightier / @DavidDWork
All U Can Heat / @AllUCanHeat 
Sports Overdose / @SportsOverdose
South Beach Beat / @ChrisPerk
Heat Gab / @HeatGab""",
            'players': """Ray Allen / @greenrayn20
Joel Anthony / @JoelAnthony50
Shane Battier / @ShaneBattier
Chris Bosh / @chrisbosh
Mario Chalmers / @mchalmers15
Norris Cole / @PG30_MIA
Udonis Haslem / ThisisUD
LeBron James / @KingJames
Mike Miller / @m33m
Jarvis Varnado / @RealSwat32
Dwyane Wade / @DwyaneWade""",
            'execs': "Micky Arison / Owner / @MickyArison",
            'mascot': "Burnie / @BurnieTheMascot",
            },
            {
            'name':'bucks',
            'team_twitter': "Milwaukee Bucks  / @Bucks",
            'writers': """Charles Gardner / Journal Sentinel / @cfgardner
Gery Woelfel / Journal Times / @gerywoelfel 
Alex Boeder / Bucks.com / @alexboeder""",
            'blogs': """Bucksketball / @bucksketball
Brew Hoop / @brewhoop
We're Bucked / @AnaheimAmigos""",
            'players': """Gustavo Ayon / @Gustavo_Ayon15
Marquis Daniels / @Marquis_Daniels
Drew Gooden / @DrewGooden
John Henson / @_John_Henson_
Ersan Ilyasova / @Ilyasova_Ersan
Brandon Jennings / @BRAND0NJENNINGS
Luc Mbah a Moute / @MbahaMoute
J.J. Redick / @JJRedick
Larry Sanders / @LarrySanders
Ishmael Smith / @ishsmith
Ekpe Udoh / @EkpeUdoh""",
            'arena': "Bradley Center / @BradleyCenter",
            'mascot': "Bango / @BucksBango",
            },
            {
            'name':'timberwolves',
            'team_twitter': "Minnesota Timberwolves / @MNTimberwolves",
            'writers': """Jerry Zgoda / Star Tribune / @JerryZgoda
Ray Richardson / Pioneer Press / @TWolvesNow
Jon Krawcyznski / AP / @apcrawcyznski
Mark Remme / Timberwolves.com / @MarkRemme
Joan Niesen / Fox Sports North / @JoanNiesen""",
            'blogs': """A Wolf Among Wolves / @mdotbrown / @talkhoops 
Dunking with Wolves / @DWWdotcom
Canis Hoopus / @canishoopus
Howlin' T-Wolf / @HowlinTWolf
Punch-Drunk Wolves / @PDWolves""",
            'players': """Jose Barea / @jjbareapr
Chase Budinger / @CBudinger
Dante Cunningham / @DlamarC33
Malcolm Lee / @leezy3
Kevin Love / @kevinlove
Ricky Rubio / @rickyrubio9
Alexey Shved / @Shved23
Greg Stiemsma / @gregstiemsma
Derrick Williams / @RealDWill7""",
            'execs': """Chris Wright / President / @WolvesPrez
Bob Stanke / Director of Interactive Services / @BobStanke
Ted Johnson / Chief Marketing Officer / @WolvesCMO
Jeff Munneke / VP of Fan Experience / @MinnesotaMunn
Timberwolves PR  / @Twolves_PR
Timberwolves Marketing / TwolvesMktg
Alan Horton / Timberwolves Radio Play by Play / @WolvesRadio""",
            'arena': "Target Center / @TargetCenterMN",
            'mascot': "Crunch the Wolf / @WolvesCrunch",
            },
            {
            'name':'hornets',
            'team_twitter': "New Orleans Hornets / @hornets",
            'writers': """Jimmy Smith / The Times Picayune / @JimmySmithTP
John Reid / The Times Picayune / @JohnReidTP
Jim Eichenhofer / Hornets.com / @jim_eichenhofer""",
            'blogs': """Hornets 24/7 / @hornets247
At the Hive / @atthehive
Swarm and Sting / @swarmandsting""",
            'players': """Al-Farouq Aminu / @farouq1
Ryan Anderson / @ryananderson33
Anthony Davis / @AntDavis23
Eric Gordon / @TheOfficialEG10
Robin Lopez / @eegabeeva88
Roger Mason / @MoneyMase
Darius Miller / @uknum1
Austin Rivers / @AustinRivers25
Lance Thomas / @slangmagic
Greivis Vasquez / @greivisvasquez""",
            'execs': """Hugh Weber / President / @hughweber1
Hornets PR / @HornetsPR""",
            'arena': "New Orleans Arena / @NewOrleansArena",
            },
            {
            'name':'knicks',
            'team_twitter': "New York Knicks / @nyknicks",
            'writers': """Nate Taylor / New York Times / @ByNateTaylor
Frank Isola / New York Daily News / @FisolaNYDN
Marc Berman / New York Post / @NYPost_Berman
Al Iannazone / The Bergen Record / @al_iannazzone
Steve Popper / The Record / @StevePopper 
Ian Begley / ESPN New York / @IanBegley
Adam Zagoria / SNY.tv / @adamzagoria 
Jared Zwerling / ESPN New York / @JaredZwerling
Chris Herring / Wall Street Journal / @HerringWSJ""",
            'blogs': """The Knicks Blog / @TommyDeeTKB
The Knicks Blog Radio / @AnthonyMSG
Posting and Toasting / @seth_rosenthal / @charlestosborn / @giancasimiro
Knicks Journal / @KnicksJournal
KnickerBlogger / @KnickerBlogger
Buckets Over Broadway / BucketsOverBway
Knicks Now / @JonahBallow / @MauraCheeks
NYK Blog / @jg_nykb / @zb_nykb
The Knicks Wall / @TheKnicksWall
Lo Hud Knicks Blog / @LoHudKnicks
Knicks Vision / @DanMirandaNYK
Daily Knicks / @DailyKnicks
Knicks Tweets / @KnicksTweets
Knicks Knotes / @knicksknotes
From the Baseline / @fromthebaseline
Hoopsworld / @AlexRaskinNYC""",
            'players': """Carmelo Anthony / @carmeloanthony
Marcus Camby / @MarcusCamby23
Tyson Chandler / @tysonchandler
Chris Copeland / @OptimusCope
Raymond Felton / @RFeltonGBMS
Jason Kidd / @RealJasonKidd
Kenyon Martin / @KenyonMartinSr
Steve Novak / @stevenovak20
Pablo Prigioni / @PPrigioni9
Iman Shumpert / @I_Am_Iman
J.R. Smith / @TheRealJRSmith
Amare Stoudemire / @Amareisreal
James White / @Flight8""",
            'execs': """Drew Cloud / VP of Ticket Sales and Service / @drew_cloud""",
            'arena': "Madison Square Garden / @MSGnyc",
            },
            {
            'name':'thunder',
            'team_twitter': "Oklahoma City Thunder / @okcthunder",
            'writers': """Darnell Mayberry / The Oklahoman / @DarnellMayberry
John Rohde / The Oklahoman / @Rohdeok""",
            'blogs': """Daily Thunder / @dailythunder
Welcome to Loud City / @WTLC
Thunder Obsessed / @ThunderObsessed""",
            'players': """Ronnie Brewer / @RonnieBrewerJr
Nick Collison / @nickcollison4
Kevin Durant / @KDTrey5
Serge Ibaka / @sergeibaka9
Reggie Jackson / @rjOKCson_15
Perry Jones III / @Perry_Jones1
Jeremy Lamb / @jlamb
DeAndre Liggins / @Dreliggs34
Daniel Orton / @danielorton21
Thabo Sefolosha / @ThaboSefolosha
Hasheem Thabeet / @HasheemTheDream
Russell Westbrook / @russwest44""",
            'mascot': """Rumble the Bison / @rumblethebison""",
            'arena': "Chesapeake Energy Arena / @ChesapeakeArena",
            },
            {
            'name':'magic',
            'team_twitter': "Orlando Magic / @orlando_magic",
            'writers': """Josh Robbins / Orlando Sentinel / @JoshuaBRobbins
Brian Schmitz / Orlando Sentinel / @magicinsider
John Denton / OrlandoMagic.com / @JohnDenton555""",
            'blogs': """Magic Basketball / @erivera7
Howard the Dunk / @howardthedunk
Magic Basketball Online / @MagicBasketball  
Orlando Magic Daily / @omagicdaily 
Orlando Pinstriped Post / @OPPMagicBlog
Savage From the Sideline / @Dan_Savage
Cohen Courtside / @Josh_Cohen_NBA""",
            'players': """Arron Afflalo / @Arron_Afflalo
Glen Davis / @iambigbaby11
Maurice Harkless / @moe_harkless
Al Harrington / @cheddahcheese7
Tobias Harris / @tobias31
DeQuan Jones / @DequanJones5
Doron Lamb / @DLamb20
E'Twaun Moore / @ETwaun55
Jameer Nelson / @jameernelson 
Andrew Nicholson / @nicholaf44
Kyle O'Quinn / @KO_STAT_2
Hedo Turkoglu / @hidoturkoglu15
Hakim Warrick / @hdubb21""",
            'execs': """Pat Williams / SVP / @OrlandoMagicPat""",
            'arena': "Amway Center / @AmwayCenter",
            'mascot': "STUFF / @STUFF_Mascot"
            },
            {
            'name':'76ers',
            'team_twitter': "Philadelphia 76ers / @Sixers",
            'writers': """John Mitchell / Deep Sixer / @DeepSixer3
Marc Narducci / Deep Sixer / @sjnard
Bob Cooney / Sixerville / @BobCooney76
Del Lynam / Comcast SportsNet  / @dlynamCSN
Chris Vito / Delaware County Daily Times / @ChrisVito 
Tom Moore / Calkins Media / @tmooreburbs
Adam Levitan / Metro / @adamlevitan""",
            'blogs': """Liberty Ballers / @Philly76ersBlog
Philadunkia / @Philadunkia
Depressed Fan / @DepressedFan""",
            'players': """Lavoy Allen / @Mr_5Hundred
Spencer Hawes / @spencerhawes00
Jrue Holiday / @Jrue_Holiday11
Royal Ivey / @ROYALTIVEY
Charles Jenkins / @CTJenkins22
Arnett Moultrie / @amoultrie
Jeremy Pargo / @DontHa8Pargo
Jason Richardson / @jrich23
Evan Turner / @thekidet
Damien Wilkins / @dwilkins3000
Dorell Wright / @DWRIGHTWAY1
Nick Young / @NickSwagyPYoung
Thaddeus Young / @yungsmoove21""",
            'execs': """Adam Aron / CEO and Co-Owner / @SixersCEOAdam
Michael Preston / Director of PR / @Preston76
Allen Lumpkin / Director of Basketball Administration / @biglumpal""",
            'arena': "Wells Fargo Center / @WellsFargoCtr",
            },
            {
            'name':'suns',
            'team_twitter': "Phoenix Suns / @Suns",
            'writers': """Paul Coro / The Arizona Republic / @paulcoro""",
            'blogs': """Valley of the Suns / @valleyofthesuns
Bright Side of the Sun / @BrightSideSun
Sun-N-Gun / @snghoops""",
            'players': """Michael Beasley / @IMABIG0
Shannon Brown / @ShannonBrown
Goran Dragic / @Goran_Dragic
Jared Dudley / @JaredDudley619
Channing Frye / @Channing_Frye
Diante Garrett / @kingarrett10
Marcin Gortat / @MGortat
Hamed Haddadi / @HamedHaddadi15
Kendall Marshall / @KButter5
Marcus Morris / @MookMorris2
Markieff Morris / @keefmorris
Jermaine O'Neal / @jermaineoneal
Luis Scola / @LScola4
P.J. Tucker / @PJTUCKER17""",
            'execs': """Jason Rowley / President / @JasonRowleySuns
Tanya Wheeless / SVP, Public Affairs / @TWheeless
Jeramie McPeek / VP of Digital / @jmcpeek
Greg Esposito / Social Media Specialist / @Espo
Kip Helt / VP, Game Ops / @PhxSunsGameOps
Rebecca Clark / PR Coordinator / @SunsPRgirl""",
            'arena': "US Airways Center / @USAirwaysCenter",
            },
            {
            'name':'trail blazers',
            'team_twitter': "Portland Trail Blazers / @pdxtrailblazers",
            'writers': """Joe Freeman / The Oregonian / @BlazerFreeman
Chris B. Haynes / Comcast NW / @ChrisBHaynes
Jason Quick / The Oregonian / @jwquick
Kerry Eggers / Portland Tribune / @kerryeggers
Candace Buckner / The Columbian / @blazerbanter""",
            'blogs': """Rip City Project / @ripcityproject
Blazers Edge / @blazersedge
Portland Roundball Society / @pdxroundball""",
            'players': """LaMarcus Aldridge / @aldridge_12
Luke Babbitt / @LukeBabbitt8
Will Barton / @WillTheThrillB5
Nicolas Batum / @nicolas88batum
Victor Claver / @Victor_Claver
J.J. Hickson / @JJHickson31
Meyers Leonard / @MeyersLeonard11
Damian Lillard / @Dame_Lillard
Wesley Matthews / @wessywes2
Eric Maynor / @EYMaynor3
Nolan Smith / @NdotSmitty
Elliot Williams / @ewill901""",
            'execs': """Paul Allen / Owner / @PaulGAllen
Jim Taylor / Senior Director of Communications / @BlazerFlack
Trail Blazers Public Relations / @TrailblazersPR""",
            'arena': "Rose Garden / @rosequarter",
            },
            {
            'name':'kings',
            'team_twitter': "Sacramento Kings / @sacramentokings",
            'writers': """Jason Jones / Sacramento Bee / @mr_jasonjones
Matthew Kawahara / Sacramento Bee / @matthewkawahara
Ailene Voisin / Sacramento Bee / @ailene_voisin""",
            'blogs': """Cowbell Kingdom / @cowbell_kingdom
Sactown Royalty / @sactownroyalty / @teamziller
A Royal Pain / @aroyalpain
Bleed Black and Purple / @blakeellington
Blue Man Hoop / @BlueManHoop
Kings Gab / @KingsGab
Evil Cowtown, Inc. / @KingsGuru  
Kings Talking Points / @RonWenig""",
            'players': """Cole Aldrich / @colea45
Aaron Brooks / @Thirty2zero
DeMarcus Cousins / @boogiecousins
Tyreke Evans / @TyrekeEvans
Jimmer Fredette / @jimmerfredette
Chuck Hayes / @c_hayes44
Travis Outlaw / @SippiCountryBoi
Patrick Patterson / @pdpatt
John Salmons / @BucSalmons
Isaiah Thomas / @Isaiah_Thomas2
Jason Thompson / @jtthekid
Marcus Thornton / @OfficialMT23""",
            'execs': """Gavin Maloof / Vice Chairman and Co-Owner / @GavMaloof
Joe Maloof / President and Co-Owner / @JoeMaloof
Chris Clark / Director of Public Relations / @C2KingsPR""",
            'arena': "Power Balance Pavilion / @pbpav",
            'mascot': "Slamson the Lion / @SlamsonTheLion"
            },
            {
            'name':'spurs',
            'team_twitter': "San Antonio Spurs / @spurs",
            'writers': """Jeff McDonald / San Antonio Express-News / @JMcDonald_SAEN
Mike Monroe / San Antonio Express-News / @Monroe_SA 
Dan McCarney / Spurs Nation, San Antonio Express / @danmccarneysaen""",
            'blogs': """Project Spurs / @projectspurs
48 Minutes of Hell / @varner48moh
Pounding the Rock / @poundingtherock
Spurs of the Moment / @spursreloaded
Air Alamo / @AirAlamo 
Club Spurs / @ClubSpurs
Spurs Dynasty / @SpursDynasty""",
            'players': """Aron Baynes / @aronbaynes
DeJuan Blair / @DeJuan45
Nando de Colo / @NandoDeColo
Boris Diaw / @theborisdiaw
Manu Ginobili / @manuginobili
Danny Green / @dgreen_14
Stephen Jackson / @DaTrillStak5
Cory Joseph / @Cory_Joe
Kawhi Leonard / TheBig_Island
Patrick Mills / @Patty_Mills
Gary Neal / @GNeal14
Tony Parker / @tp9network
Tiago Splitter / @tiagosplitter""",
            'arena': "Power Balance Pavilion / @pbpav",
            'mascot': "The Coyote / @SpursCoyote"
            },
            {
            'name':'raptors',
            'team_twitter': "Toronto Raptors / @raptors",
            'writers': """Doug Smith / The Toronto Star / @SmithRaps
Cathal Kelly / The Toronto Star / @cathalkelly
Ryan Wolstat / Toronto Sun / @WolstatSun
Mike Ganter / Toronto Sun / @Mike_Ganter 
Eric Koreen / National Post / @ekoreen
Michael Grange / Rogers Sportsnet / @michaelgrange
Lori Ewing / The Canadian Press / @Ewingsports
Ian Harrison / AP / @iananywhere""",
            'blogs': """Dino Nation Blog / @dinonationblog
Raptor Blog / @scottcarefoot
Cuzoogle / @cuzoogle
Heels on Hardwood / @Nat77
Inside the Purple Room / @PayalDoshiTV
Raptors Forum / @RaptorsForum 
Raptors HQ / @RaptorsHQ 
Raptors Republic / @RaptorsRepublic""",
            'players': """Quincy Acy / @QuincyAcy
Andrea Bargnani / @andreabargnani
DeMar DeRozan / @DeMar_DeRozan
Landry Fields / @landryfields
Rudy Gay / @rudygay22
Amir Johnson / @iamamirjohnson
Linas Kleiza / @linas_kleiza
Kyle Lowry / @Klow7
John Lucas / @Luke1luk
Mickael Pietrus / @MickaelPietrus
Terrence Ross / @T_DotFlight31
Sebastian Telfair / @BassyS31T""",
            'execs': """Jim LaBumbard / Director of Media Relations / @jlombo07
Raptors PR / @RaptorsPR""",
            'arena': "Air Canada Centre / @ACC_Events",
            'mascot': "The Raptor / @the_raptor"
            },
            {
            'name':'jazz',
            'team_twitter': "Utah Jazz / @utahjazz",
            'writers': """Brian T. Smith / Salt Lake Tribune / @tribjazz
Steve Luhm / Salt Lake Tribune / @sluhm
Jody Genessy / Deseret News / @DJJazzyJody
Jim Burton / Standard-Examiner / @jmb247""",
            'blogs': """Salt City Hoops / @saltcityhoops
SLC Dunk / @slcdunk
Chuck Nunn's Jazz Oracle / @CnunnJazz
The Utah Jazz Blog / @theutahjazzblog
Jazz Fanz / @jazzfanz
Jazz Fanatical / @monilogue""",
            'players': """Alec Burks / @AlecBurks10
DeMarre Carroll / @DeMarreCarroll1
Jeremy Evans / @JeremyEvans40
Derrick Favors / @DFavors14/ 
Randy Foye / @randyfoye
Gordon Hayward / @gordonhayward
Enes Kanter / @Enes_Kanter
Paul Millsap / @PaulMillsap_24
Jamaal Tinsley / @jatinsley
Mo Williams / @mowilliams""",
            'execs': """Greg Miller / CEO / @GreginUtah 
Jonathan Rinehart / Director of PR / @jonrinehart""",
            'arena': "EnergySolutions Arena / @ESArenaOfficial",
            'mascot': "Jazz Bear / @utahjazzbear"
            },
            {
            'name':'wizards',
            'team_twitter': "Washington Wizards / @WashWizards",
            'writers': """Michael Lee / The Washington Post / @MrMichaelLee
Carla Peay / The Washington Times / @ckpeay
Craig Stouffer / The Washington Examiner / @craigstouffer""",
            'blogs': """Truth About It / @Truth_About_It
Bullets Forever / @BulletsForever
Wizards Extreme / @WizardsExtreme
Wiz Kid / @Mr_KevinJones""",
            'players': """Trevor Ariza / @TrevorAriza
Leandro Barbosa / @leandrinhooo20
Bradley Beal / @RealDealBeal23
Trevor Booker / @trevor_booker
Jason Collins / @jasoncollins34
Cartier Martin / @CartierMartin
Emeka Okafor / @BigMek50
A.J. Price / @realajprice
Kevin Seraphin / @kevin_seraphin
Chris Singleton / @C_Sing31
Garrett Temple / @GTemp14 
Jan Vesely / @JanVesely24
John Wall / @John_Wall
Martell Webster / @MartellWebster""",
            'arena': "Verizon Center / @verizoncenterpr",
            'mascot': "G-Wiz / @the_real_Gwiz"
            }
        ]
        for team_info in teams:
            team = session.query(Team).filter_by(name=team_info['name']).one()
            team_twitter = team_info['team_twitter'].split(' / @')[1]
            '''
            writer_handles = team_info['writers'].split('\n')
            for handle in writer_handles:
                writer_name, source_name, handle = handle.split(' / ')
                source_name = u'%s'.encode("utf-8") % source_name
                source = session.query(Source)\
                                .filter(Source.full_name==source_name)\
                                .first()
                if not source:
                    source = Source(full_name=source_name, name=source_name)
                    session.add(source)
                    session.commit()
                try:
                    writer = session.query(Writer)\
                                    .join(Person, PersonName)\
                                    .filter(PersonName.full_name==writer_name)\
                                    .one()
                except NoResultFound:
                    person = Person()
                    session.add(person)
                    session.commit()
                    name = PersonName(full_name=writer_name, person_id=person.id)
                    session.add(name)
                    session.commit()
                    writer = Writer(person_id=person.id)
                    session.add(writer)
                    session.commit()
                twitter, c = get_or_create(session, Twitter, 
                                           handle=handle, name=writer_name, 
                                           person_id=person.id, 
                                           source_name=source_name)
            blog_handles = team_info['blogs'].split('\n')
            for handle in blog_handles:
                source_name, a, blog_handles = handle.partition(' / ')
                source_name = u'%s'.encode("utf-8") % source_name
                source = session.query(Source)\
                                .filter(Source.full_name==source_name)\
                                .first()
                if not source:
                    source = Source(full_name=source_name, name=source_name)
                source.source_type = 'blog'
                session.add(source)
                session.commit()
                if blog_handles:
                    blog_handles = blog_handles.split(' / ')
                    for handle in blog_handles:
                        twitter, c = get_or_create(session, Twitter, 
                                                   handle=handle, 
                                                   source_name=source_name)
            '''
            player_handles = team_info['players'].split('\n')
            for handle in player_handles:
                player_name, handle = handle.split(' / ')
                player_name = u'%s'.encode("utf-8") % player_name
                player = session.query(Player)\
                                .join(Person, PersonName, League)\
                                .filter(PersonName.full_name==player_name, 
                                        League.abbr=='nba').one()
                twitter, c = get_or_create(session, Twitter, 
                                           handle=handle,
                                           name=player_name,
                                           person_id=player.person.id)
                                        
                
                
        
    
    
    
