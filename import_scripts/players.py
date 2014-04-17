import csv
import datetime
import urllib, urllib2
from BeautifulSoup import BeautifulSoup
from sqlalchemy.orm.exc import NoResultFound
from connect_db import *
from bizarro.models.teams import *
from bizarro.models.people import *
from helpers import get_or_create_player, create_full_player
from nfl.players import import_roster as nfl_roster

def team_players(team, next_url=None):
    city = team.city.replace(' ', '_')
    team_name = team.name.replace(' ', '_')
    url = 'http://en.wikipedia.org/wiki/Category:%s_%s_players' 
    url %= (city, team_name)
    if next_url:
        url = next_url
    req = urllib2.Request(url)
    req.add_header('user-agent', 'http://www.hello.com')
    result = urllib2.urlopen(req)
    body = BeautifulStoneSoup(result)
    #for letter in string.uppercase:
    letters = body.findAll('h3')
    players = []
    for b in letters:
        if not b.text == '*':
            these_players = b.findNext('ul').findAll('li')
            for player in these_players:
                players.append(player)
    for player in players:
        if not player.a:
            pass
        else:
            try:
                name = player.a['title'].strip()
                if '(' in name:
                    name = name[:name.find('(')].strip()
                if name.find('all-time') >= 0:
                    pass
                else:
                    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
                    player = create_person(Player, name)
                    team_player = get_or_create(TeamPersonnel, player_id=player.id, team_id = team.id)
                    save(team_player)
                             
            except KeyError:
                if player.a['class'] == 'CategoryTreeLabel  CategoryTreeLabelNs14 CategoryTreeLabelCategory':
                    pass
                else:
                    pass
    next_page = body.find('a', text='next 200')
    if next_page:
        next_url = 'http://en.wikipedia.org/%s' % next_page.parent['href']
        team_players(team, next_url)

def import_roster(league_abbr):
    session = create_session()
    league = session.query(League).filter_by(abbr=league_abbr).one()
    teams = session.query(Team)\
                   .join(LeagueTeam)\
                   .filter(LeagueTeam.league_id==league.id)
    '''
    for team in teams:
        players = session.query(TeamPlayer)\
                         .filter_by(team_id=team.id)\
                         .update({'current':False})
        session.commit()
    '''
    if league.abbr == 'nfl':
        nfl_roster(league, teams)
    elif league.abbr == 'nba':
        league = session.query(League).filter_by(abbr=league).one()
        sport = 'basketball'
        teams = session.query(Team)\
                       .join(LeagueTeam)\
                       .filter(LeagueTeam.league_id==league.id)
        source, created = get_or_create(session, Source, name='espn')
        for team in teams:
            print team.abbr
            url = 'http://espn.go.com/nba/team/roster/_/name/%s/' % team.abbr
            result = urllib2.urlopen(url)
            body = BeautifulSoup(result)
            coach = body.find('strong', text='Coach:')
            if coach:
                coach = coach.findNext('a')
                coach_name = coach.text
                external_id = coach['href'].partition('id/')[2].\
                                            partition('/')[0]
                coach_external_id, created = get_or_create(session, 
                                                    CoachExternalID, 
                                                    source_name=source.name, 
                                                    league_id=league.id, 
                                                    external_id=external_id)
                coach = coach_external_id.coach
                if not coach:
                    person = Person()       
                    person = save(session, person)
                    coach = Coach(person_id=person.id, league_id=league.id)
                    coach = save(session, coach)
                    coach_external_id.coach = coach
                    save(session, coach_external_id)
                else:
                    person = coach.person              
                coach_name, created = get_or_create(session, PersonName, 
                                                    full_name=coach_name, 
                                                    person_id=person.id)
                team_coach, created = get_or_create(session, TeamCoach,
                                                    coach_id=coach.id,
                                                    team_id=team.id,
                                                    coach_type='head',
                                                    current=True)
            player_search = r'evenrow|oddrow player'
            players= body.findAll('tr', 
                        attrs={'class':re.compile(player_search)})
            if not players:
                raise Exception('no players exist for this team')
            for player_row in players:
                info = player_row.findAll('td') 
                number = info[0].text        
                full_name = info[1].text
                external_id = info[1].a['href'].partition('id/')[2].\
                                            partition('/')[0]
                position = info[2].text.lower()
                height = info[4].text.partition('-')
                feet = int(height[0])
                inches = int(height[2])
                height = feet*12 + inches
                weight = int(info[5].text)
                college = info[6].text.replace(';', '').\
                                       replace('&nbsp', '').strip()
                player = create_player(session, full_name, external_id, height, 
                                       weight, college, league, team, source, 
                                       position, number, sport)
