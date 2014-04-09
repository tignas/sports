from dateutil import parser
from sqlalchemy.orm.exc import NoResultFound
from connect_db import *
from bizarro.models.teams import Sport, League
from bizarro.models.stats import Season

def create_sports():
    session = create_session()    
    sports = [
        'basketball',
        'hockey',
        'football',
        'baseball',
        'soccer',
        'golf',
        'tennis',
        'lacrosse',
        'cricket',
        'driving',
        'poker',
        'swimming',
        'track',
        'badminton',
        'volleyball',
        'polo',
        'horse racing',
        'rugby',
        'billiards',
        'handball',
    ]
    for sport in sports:
        if not session.query(Sport).filter_by(name=sport).exists():
            sport = Sport(name=sport)
            session.add(sport)
            print 'added sport %s' % sport.name
    session.commit()

def get_location(location_name):
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s&sensor=false' 
    url %= urllib.urlencode({'address': location_name})
    location = json.load(urllib2.urlopen(url))
    try:
        results = location['results'][0]
    except IndexError:
        print url
        print location_name
        raise Exception('whoops')
    address = results['address_components']
    location = Location()
    for component in address:
        if 'country' in component['types']:
            location.country = component['long_name']
        elif 'administrative_area_level_1'  in component['types']:
            location.state = component['long_name']
        elif 'administrative_area_level_2' in component['types']:
            location.county = component['long_name']
        elif 'administrative_area_level_3' in component['types']:
            location.town = component['long_name']
        elif 'locality' in component['types']:
            location.city = component['long_name']
        elif 'sublocality' in component['long_name']:
            location.sublocality = component['long_name']
        elif 'neighborhood' in component['types']:
            location.neighborhood = component['long_name']    
    location.longitude = results['geometry']['location']['lng']
    location.latitude = results['geometry']['location']['lat']
    location_query = session.query(Location).\
                        filter_by(longitude=location.longitude,
                        latitude=location.latitude).first()
    if not location_query:         
        session.add(location)
        session.commit()
    else:
        location = location_query
    return location

def get_address(address):     
    location = get_location(address)
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s&sensor=false'
    url %= urllib.urlencode({'address': address})
    address = json.load(urllib2.urlopen(url))
    results = address['results'][0]
    address_components = results['address_components']   
    address = Address(location_id=location.id)
    for component in address_components:
        if 'postal_code' in component['types']:
            address.postal_code = component['long_name']
        elif 'route' in component['types']:
            address.street = component['long_name']
        elif 'street_number' in component['types']:
            address.street_number = component['long_name']
    address_query = session.query(Address).filter_by(location_id=location.id, 
                                        street_number=address.street_number, 
                                        street=address.street).first()
    if not address_query:         
        session.add(address)
        session.commit()
    else:
        address = address_query
    return address

def create_league(league):
    if league == 'nfl':
        #League
        full_name ='national football league'
        sport = 'football'
        abbr = 'nfl'
        website ='http://www.nfl.com/'
        start_date = datetime.date(month=9, year=1920, day=17)
        founded_location_id = get_address('princeton, nj').id
        address_id = get_location('345 park avenue, new york ny').id
        league, created = get_or_create(session, League,full_name=full_name, 
                            abbr=abbr, website=website,
                            start_date=start_date,
                            founded_location_id=founded_location_id, 
                            address_id=address_id,
                            sport_name=sport)
        #Conferences
        afc, created = get_or_create(session, Conference, 
                        name='american football conference', abbr='afc', 
                        start_date=datetime.date(year=1970, month=1, day=1),
                        league_id=league.id)
        nfc,created = get_or_create(session, Conference, 
                        name='national football conference', abbr='nfc',
                        start_date=datetime.date(year=1970, month=1, day=1),
                        league_id=league.id)
        #Divisions
        divisions = ['east', 'west', 'north', 'south']
        for division_name in divisions:
            for conference in [afc, nfc]:
                abbr = '%s %s' % (conference.abbr, division_name)
                division, created = get_or_create(session, Division,
                                        league_id=league.id, abbr=abbr)
                div_conf, created = get_or_create(session, DivisionConference,
                                    division_id=division.id,
                                    conference_id=conference.id)
        #Teams
        teams = {
            'dal': {'location': 'dallas', 'name': 'cowboys'},
            'nyg': {'location': 'new york', 'name': 'giants'},
            'phi': {'location': 'philadelphia', 'name': 'eagles'},
            'wsh': {'location': 'washington', 'name': 'redskins'},
            'ari': {'location': 'arizona', 'name': 'cardinals'},
            'sf': {'location': 'san francisco', 'name': '49ers'},
            'sea': {'location': 'seattle', 'name': 'seahawks'},
            'stl': {'location': 'st. louis', 'name': 'rams'},
            'chi': {'location': 'chicago', 'name': 'bears'},
            'det': {'location': 'detroit', 'name': 'lions'},
            'gb': {'location': 'green bay', 'name': 'packers'},
            'min': {'location': 'minnesota', 'name': 'vikings'},
            'atl': {'location': 'atlanta', 'name': 'falcons'},
            'car': {'location': 'carolina', 'name': 'panthers'},
            'no': {'location': 'new orleans', 'name': 'saints'},
            'tb': {'location': 'tampa bay', 'name': 'buccaneers'},
            'buf': {'location': 'buffalo', 'name': 'bills'},
            'mia': {'location': 'miami', 'name': 'dolphins'},
            'ne': {'location': 'new england', 'name': 'patriots'},
            'nyj': {'location': 'new york', 'name': 'jets'},
            'den': {'location': 'denver', 'name': 'broncos'},
            'kc': {'location': 'kansas city', 'name': 'chiefs'},
            'oak': {'location': 'oakland', 'name': 'raiders'},
            'sd': {'location': 'san diego', 'name': 'chargers'},
            'bal': {'location': 'baltimore', 'name': 'ravens'},
            'cin': {'location': 'cincinnati', 'name': 'bengals'},
            'cle': {'location': 'cleveland', 'name': 'browns'},
            'pit': {'location': 'pittsburgh', 'name': 'steelers'},
            'hou': {'location': 'houston', 'name': 'texans'},
            'ind': {'location': 'indianapolis', 'name': 'colts'},
            'jac': {'location': 'jacksonville', 'name': 'jaguars'},
            'ten': {'location': 'tennessee', 'name': 'titans'},
        }
        for abbr, team in teams.items():
            team, created = get_or_create(session, Team,
                            location=team['location'],
                            name=team['name'], abbr=abbr, 
                            sport_name=sport)
            league_team, created = get_or_create(session, LeagueTeam,
                                        team_id=team.id, league_id=league.id)
        #Set divisions
        divs = {'nfc': {
                    'east': ['dal', 'nyg', 'phi', 'wsh'],
                    'west': ['ari', 'sf', 'sea', 'stl'],
                    'north': ['chi', 'det', 'gb', 'min'],
                    'south': ['atl', 'car', 'no', 'tb'],
                },
                'afc': {
                    'east': ['buf', 'mia', 'ne', 'nyj'],
                    'west': ['den', 'kc', 'oak', 'sd'],
                    'north': ['bal', 'cin', 'cle', 'pit'],
                    'south': ['hou', 'ind', 'jac', 'ten'],
                }
                }
        for conf, divisions in divs.items():
            for division, teams in divisions.items():                
                division_name = '%s %s' % (conf, division)
                division = session.query(Division).\
                                filter_by(abbr=division_name).first()
                for abbr in teams:
                    team = session.query(Team).filter_by(abbr=abbr).first()
                    team_div, created = get_or_create(session, DivisionTeam,
                                division_id=division.id,
                                team_id=team.id)
        positions = {
            'qb': 'quarterback',
            'rb': 'running back',
            'fb': 'full back',
            'hb': 'half back',
            'te': 'tight end',
            'wr': 'wide receiver',
            'c': 'center',
            'g': 'guard',
            'rg': 'right guard',
            'rt': 'right tackle',
            'og': 'offensive guard',
            'ol': 'offensive lineman',
            'lg': 'left guard',
            'lt': 'left tackle',
            'ot': 'offensive tackle',
            'lb': 'linebacker',
            'mlb': 'middle linebacker',
            'olb': 'outside linebacker',
            'lolb': 'left outside linebacker',
            'rolb': 'right outside linebacker',
            'dt': 'defensive tackle',
            'cb': 'cornerback',
            'db': 'defensive back',
            's': 'safety',
            'ss': 'strong safety',
            'fs': 'free safety',
            'de': 'defensive end',
            'le': 'left end',
            're': 'right end',
            't': 'tackle',
            'nt': 'nose tackle',
            'ls': 'long snapper',
            'p': 'punter',
            'pk': 'place kicker',
            'k': 'kicker',
            'h': 'holder',
            'pr': 'punt returner',
            'kr': 'kick returner',
            'kos': 'kickoff specialist',
            'ath': 'athlete',
        }
        for abbr, name in positions.items():
            position, created = get_or_create(session, Position,
                                abbr=abbr, name=name, 
                                sport_name=sport)
        
        seasons = {
        '2004': {
        'preseason_start': '08/12/04',
        'preseason_end': '09/03/04',
        'regular_start': '09/09/04', 
        'regular_end': '01/02/05',
        'postseason_start': '01/08/05',
        'postseason_end': '02/06/05',
        },
        '2005': {
        'preseason_start': '08/11/05',
        'preseason_end': '09/02/05',
        'regular_start': '09/08/05',
        'regular_end': '01/01/06',
        'postseason_start': '01/07/06',
        'postseason_end': '02/05/06',
        },
        '2006': {
        'preseason_start': '08/10/06',
        'preseason_end': '09/01/06',
        'regular_start': '09/07/06',
        'regular_end': '12/31/06',
        'postseason_start': '01/06/07',
        'postseason_end': '02/04/07',
        },
        '2007': {
        'preseason_start': '08/09/07',
        'preseason_end': '08/31/07',
        'regular_start': '09/06/07',
        'regular_end': '12/30/07',
        'postseason_start': '01/05/08',
        'postseason_end': '02/03/08',
        },
        '2008': {
        'preseason_start': '08/03/08',
        'preseason_end': '08/29/08',
        'regular_start': '09/04/08',
        'regular_end': '12/28/08',
        'postseason_start': '01/03/09',
        'postseason_end': '02/01/09',
        },
        '2009': {
        'preseason_start': '08/09/09',
        'preseason_end': '09/04/09',
        'regular_start': '09/10/09',
        'regular_end': '01/03/10',
        'postseason_start': '01/09/10',
        'postseason_end': '02/07/10',
        },
        '2010': {
        'preseason_start': '08/08/10',
        'preseason_end': '09/02/10',
        'regular_start': '09/09/10',
        'regular_end': '01/02/11',
        'postseason_start': '01/08/11',
        'postseason_end': '02/06/11',
        },
        '2011': {
        'preseason_start': '08/07/11',
        'preseason_end': '09/02/11',
        'regular_start': '09/08/11',
        'regular_end': '01/01/12',
        'postseason_start': '01/07/12',
        'postseason_end': '02/05/12',
        },
        '2012': {
        'preseason_start': '08/05/12',
        'preseason_end': '08/30/12',
        'regular_start': '09/05/12',
        'regular_end': '12/30/12',
        'postseason_start': '01/05/13',
        'postseason_end': '02/03/13',
        },
        '2013': {
        'preseason_start': '08/04/13',
        'preseason_end': '08/29/13',
        'regular_start': '09/05/13',
        'regular_end': '12/29/13',
        'postseason_start': None,
        'postseason_end': None,
        },
        }
        for year, dates in seasons.items():
            for date_type, date in dates.items():
                if date:
                    date = parser.parse(date).date()
                dates[date_type] = date
            dates.update({'league_id': 1, 'year': year})
            season = Season(**dates)
            session.add(season)
        session.commit()
    elif league == 'nba':
        #League
        full_name ='national basketball association'
        abbr = 'nba'
        sport = 'basketball'
        website ='http://www.nba.com/'
        start_date = datetime.date(month=6, year=1946, day=6)
        founded_location = get_location('manhattan, ny')
        address_id = get_location('645 Fifth Avenue New York, NY 10022').id
        league, created = get_or_create(session, League, full_name=full_name, 
                            abbr=abbr, website=website, start_date=start_date,
                            founded_location_id=founded_location.id, 
                            address_id=address_id, sport_name=sport)
        #Conferences
        east, created = get_or_create(session, Conference, 
                        name='eastern conference', abbr='east',
                        start_date=datetime.date(year=1947, month=1, day=1),
                        league_id=league.id)
        west, created = get_or_create(session, Conference, 
                        name='western conference', abbr='west',
                        start_date=datetime.date(year=1947, month=1, day=1),
                        league_id=league.id)
        #Divisions
        divisions_by_conference = {
            east: ['atlantic', 'central', 'southeast'],
            west: ['northwest', 'pacific', 'southwest'],
        }
        for conference, division_names in divisions_by_conference.items():
            for name in division_names:
                division, created = get_or_create(session, Division,
                                        league_id=league.id, name=name)
                div_conf, created = get_or_create(session, DivisionConference,
                                    division_id=division.id,
                                    conference_id=conference.id)
        #Teams
        teams = {
            'bos': {'location': 'boston', 'name': 'celtics'},
            'bkn': {'location': 'brooklyn', 'name': 'nets'},
            'ny': {'location': 'new york', 'name': 'knicks'},
            'phi': {'location': 'philadelphia', 'name': '76ers'},
            'tor': {'location': 'toronto', 'name': 'raptors'},
            'chi': {'location': 'chicago', 'name': 'bulls'},
            'cle': {'location': 'cleveland', 'name': 'cavaliers'},
            'det': {'location': 'detroit', 'name': 'pistons'},
            'ind': {'location': 'indiana', 'name': 'pacers'},
            'mil': {'location': 'milwaukee', 'name': 'bucks'},
            'atl': {'location': 'atlanta', 'name': 'hawks'},
            'cha': {'location': 'charlotte', 'name': 'bobcats'},
            'mia': {'location': 'miami', 'name': 'heat'},
            'orl': {'location': 'orlando', 'name': 'magic'},
            'wsh': {'location': 'washington', 'name': 'wizards'},
            'den': {'location': 'denver', 'name': 'nuggets'},
            'min': {'location': 'minnesota', 'name': 'timberwolves'},
            'okc': {'location': 'oklahoma city', 'name': 'thunder'},
            'por': {'location': 'portland', 'name': 'trail blazers'},
            'utah': {'location': 'utah', 'name': 'jazz'},
            'gs': {'location': 'golden state', 'name': 'warriors'},
            'lac': {'location': 'los angeles', 'name': 'clippers'},
            'lal': {'location': 'los angeles', 'name': 'lakers'},
            'pho': {'location': 'phoenix', 'name': 'suns'},
            'sac': {'location': 'sacramento', 'name': 'kings'},
            'dal': {'location': 'dallas', 'name': 'mavericks'},
            'hou': {'location': 'houston', 'name': 'rockets'},
            'mem': {'location': 'memphis', 'name': 'grizzlies'},
            'no': {'location': 'new orleans', 'name': 'hornets'},
            'sa': {'location': 'san antonio', 'name': 'spurs'},
        }
        for abbr, team in teams.items():
            team, created = get_or_create(session, Team,
                                        location=team['location'], abbr=abbr,
                                        name=team['name'], sport_name=sport)
            league_team, created = get_or_create(session, LeagueTeam,
                                        team_id=team.id, league_id=league.id)
        #Set divisions
        divisions = {
            'east': {
                'atlantic': ['bos', 'bkn', 'ny', 'phi', 'tor'],
                'central': ['chi', 'cle', 'det', 'ind', 'mil'],
                'southeast': ['atl', 'cha', 'mia', 'orl', 'wsh'],
            },
            'west': {
                'northwest': ['den', 'min', 'okc', 'por', 'utah'],
                'pacific': ['gs', 'lac', 'lal', 'pho', 'sac'],
                'southwest': ['dal', 'hou', 'mem', 'no', 'sa'],
            }
        }
        for conference, divisions in divisions.items():
            for division_name, teams in divisions.items():
                division = session.query(Division).\
                                filter_by(name=division_name,
                                league_id=league.id).one()
                for abbr in teams:
                    print abbr
                    team = session.query(Team).join(LeagueTeam).\
                                filter(LeagueTeam.league_id==league.id).\
                                filter(Team.abbr==abbr).one()
                    team_div, created = get_or_create(session, DivisionTeam,
                                                    division_id=division.id,
                                                    team_id=team.id)
        positions = {
            'pg': 'point guard',
            'sg': 'shooting guard',
            'g': 'guard',
            'sf': 'small forward',
            'pf': 'power forward',
            'f': 'forward',
            'c': 'center',            
        }
        for abbr, name in positions.items():
            position, created = get_or_create(session, Position,
                                abbr=abbr, name=name, 
                                sport_name=sport)        
        season_dates = {
        2012: {'regular_start':'2012-10-30', 'regular_end':'2013-04-17',
               'preseason_start':'2012-10-05', 'preseason_end':'2012-10-26', 
               'postseason_start':'2013-04-20', 'postseason_end':None},
        2011: {'regular_start':'2011-12-25', 'regular_end':'2012-04-26',
               'preseason_start':'2011-12-16', 'preseason_end':'2011-12-22', 
               'postseason_start':'2012-04-28', 'postseason_end':'2012-06-21'},
        2010: {'regular_start':'2010-10-26', 'regular_end':'2011-04-13',
               'preseason_start':'2010-10-03', 'preseason_end':'2010-10-22', 
               'postseason_start':'2011-04-16', 'postseason_end':'2011-06-12'},
        2009: {'regular_start':'2009-10-27', 'regular_end':'2010-04-14',
               'preseason_start':'2009-10-01', 'preseason_end':'2009-10-23', 
               'postseason_start':'2010-04-17', 'postseason_end':'2010-06-17'},
        2008: {'regular_start':'2008-10-28', 'regular_end':'2009-04-16',
               'preseason_start':'2008-10-05', 'preseason_end':'2008-10-24', 
               'postseason_start':'2009-04-08', 'postseason_end':'2009-06-14'},
        2007: {'regular_start':'2007-10-30', 'regular_end':'2008-04-16',
               'preseason_start':'2007-10-06', 'preseason_end':'2007-10-26',
               'postseason_start':'2008-04-19', 'postseason_end':'2008-06-17'},
        2006: {'regular_start':'2006-10-31', 'regular_end':'2007-04-18',
               'preseason_start':'2006-10-10', 'preseason_end':'2006-10-27',
               'postseason_start':'2007-04-21', 'postseason_end':'2007-06-14'},
        2005: {'regular_start':'2005-11-01', 'regular_end':'2006-04-19',
               'preseason_start':'2005-10-11', 'preseason_end':'2005-10-28',
               'postseason_start':'2006-04-22', 'postseason_end':'2006-06-20'},
        2004: {'regular_start':'2004-11-02', 'regular_end':'2005-04-20',
               'preseason_start':'2004-10-10', 'preseason_end':'2004-10-29',
               'postseason_start':'2005-04-23', 'postseason_end':'2005-06-23'},
        2003: {'regular_start':'2003-10-28', 'regular_end':'2004-04-14',
               'preseason_start':'2003-10-06', 'preseason_end':'2003-10-24',
               'postseason_start':'2004-04-17', 'postseason_end':'2004-06-15'},
        2002: {'regular_start':'2002-10-29', 'regular_end':'2003-04-16',
               'preseason_start':'2002-10-06', 'preseason_end':'2002-10-25',
               'postseason_start':'2003-04-03', 'postseason_end':'2003-06-15'},
        2001: {'regular_start':'2001-10-31', 'regular_end':'2002-04-17',
               'preseason_start':None, 'preseason_end':None,
               'postseason_start':'2002-04-20', 
               'postseason_end':'2002-06-12'},        
        }
        for year, dates in season_dates.items():
            if dates[date]:
                dates[date] = datetime.datetime\
                                      .strptime(dates[date], '%Y-%m-%d')\
                                      .date()
            dates.update({'year': year,
                          'league_id': league.id})
            season, created = get_or_create(session, Season, **dates)

def update_seasons(league_abbr):
    session = create_session(True)
    league = session.query(League).filter_by(abbr=league_abbr).one()
    if league_abbr == 'nfl':
        seasons = {
            '2004': {
                'preseason_start': '08/12/04',
                'preseason_end': '09/03/04',
                'regular_start': '09/09/04', 
                'regular_end': '01/02/05',
                'postseason_start': '01/08/05',
                'postseason_end': '02/06/05',
            },
            '2005': {
                'preseason_start': '08/11/05',
                'preseason_end': '09/02/05',
                'regular_start': '09/08/05',
                'regular_end': '01/01/06',
                'postseason_start': '01/07/06',
                'postseason_end': '02/05/06',
            },
            '2006': {
                'preseason_start': '08/10/06',
                'preseason_end': '09/01/06',
                'regular_start': '09/07/06',
                'regular_end': '12/31/06',
                'postseason_start': '01/06/07',
                'postseason_end': '02/04/07',
            },
            '2007': {
                'preseason_start': '08/09/07',
                'preseason_end': '08/31/07',
                'regular_start': '09/06/07',
                'regular_end': '12/30/07',
                'postseason_start': '01/05/08',
                'postseason_end': '02/03/08',
            },
            '2008': {
                'preseason_start': '08/03/08',
                'preseason_end': '08/29/08',
                'regular_start': '09/04/08',
                'regular_end': '12/28/08',
                'postseason_start': '01/03/09',
                'postseason_end': '02/01/09',
            },
            '2009': {
                'preseason_start': '08/09/09',
                'preseason_end': '09/04/09',
                'regular_start': '09/10/09',
                'regular_end': '01/03/10',
                'postseason_start': '01/09/10',
                'postseason_end': '02/07/10',
            },
            '2010': {
                'preseason_start': '08/08/10',
                'preseason_end': '09/02/10',
                'regular_start': '09/09/10',
                'regular_end': '01/02/11',
                'postseason_start': '01/08/11',
                'postseason_end': '02/06/11',
            },
            '2011': {
                'preseason_start': '08/07/11',
                'preseason_end': '09/02/11',
                'regular_start': '09/08/11',
                'regular_end': '01/01/12',
                'postseason_start': '01/07/12',
                'postseason_end': '02/05/12',
            },
            '2012': {
                'preseason_start': '08/05/12',
                'preseason_end': '08/30/12',
                'regular_start': '09/05/12',
                'regular_end': '12/30/12',
                'postseason_start': '01/05/13',
                'postseason_end': '02/03/13',
            },
            '2013': {
                'preseason_start': '08/04/13',
                'preseason_end': '08/29/13',
                'regular_start': '09/05/13',
                'regular_end': '12/29/13',
                'postseason_start': '01/04/14',
                'postseason_end': '02/02/14',
            },
            '2014': {
                'preseason_start': '08/03/14',
                'preseason_end': '08/30/14',
                'regular_start': '09/04/14',
                'regular_end': '12/28/14',
                'postseason_start': '01/03/15',
                'postseason_end': '02/01/15',
            }
        }
        for year, dates in seasons.items():
            for date_type, date in dates.items():
                if date:
                    date = parser.parse(date).date()
                dates[date_type] = date
            try:
                season = session.query(Season)\
                                .filter_by(league_id=league.id,
                                            year=year).one()
            except NoResultFound:
                season = Season(league_id=league.id, year=year)
                session.add(season)
                session.commit()
            season.update(dates)
            session.add(season)
        session.commit()
    
    
    
