import re
import json
import datetime
import urllib
import urllib2
from pprint import pprint
from BeautifulSoup import BeautifulSoup
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from bizarro.models.meta import *
from bizarro.models.play_by_play import *
from bizarro.connect_db import *
from helpers import get_team, create_player
from pbp_helpers import *

def process_pbps(league_abbr):
    session = create_session(alt=True)
    league = session.query(League).filter_by(abbr=league_abbr).one() 
    if league.abbr == 'nba':
        bad_game_ids = ['400400517', '400400488', '400400474', '400400472', 
                        '400400471', '400400466', '400400464', '400400463', 
                        '400400462', '400400461', '310111001', '301102018',
                        '301022014', '301016024', '301016005', '301014029',
                        '301014025', '301012014', '301007138', '301003143', 
                        '301003017', '300206027', '291020012', '291018018',
                        '291012005',]
        all_star_games = ['320226031', '310220032', '300214032']
        need_to_get_to_later = ['320404012', '320125013', '310116012']
        external_game_ids = session.query(GameExternalID)\
                                   .filter(GameExternalID.pbp==False,
                                           GameExternalID.league_id==league.id)\
                                   .filter(not_(GameExternalID\
                                                     .external_id\
                                                     .in_(bad_game_ids)))\
                                   .filter(not_(GameExternalID\
                                                     .external_id\
                                                     .in_(all_star_games)))\
                                   .order_by(desc(GameExternalID.external_id))
    base_location = '/home/tignas/pyramid/bizarro/bizarro'
    base_location += '/import_scripts/html/nba/%s_play_by_play.html'
    for external_game_id in external_game_ids:
        external_id = external_game_id.external_id
        print external_id
        game = process_pbp(external_game_id)
        external_game_id.pbp=True
        session.add(external_game_id)
        session.commit()
            
def process_pbp(external_game_id):
    source_name = 'espn'    
    url = 'http://scores.espn.go.com/nba/playbyplay?gameId=%s&period=0'
    url %= external_game_id.game_id
    boxscore = urllib2.urlopen(url)
    body = BeautifulSoup(boxscore)
    game = external_game_id.game
    home_team = game.home_team
    away_team = game.away_team
    locations = [team.location for team in [home_team, away_team]] 
    period = 0
    if game.espn_id[0].external_id == 310216015:
        period = 1
    home_score = 0
    away_score = 0
    all_plays = []
    play_search = r'\even|odd\b'
    plays = body.findAll("tr", attrs={"class":re.compile(play_search)})
    for play_number, play_row in enumerate(plays):
        #Period   
        period_text = play_row.findPrevious('thead')
        period_text = period_text.tr.td.div.h4.text.lower()
        period = int(period_text[0])
        if 'overtime' in period_text:
            period += 4
        play = play_row.findAll('td')
        #Time
        time_of_game = play[0].text
        time_of_game = datetime.datetime.strptime(time_of_game, '%H:%M').time()
        #Get or create play
        if len(play) > 2:
            away_score, a, home_score = play[2].text.partition('-')
        play_info = {
            'play_number': play_number,
            'game_id': game.id,
            'source_name': source_name,
            'home_score': home_score,
            'away_score': away_score,
            'period': period,
            'time_of_game': time_of_game,
        }
        play_params = {
            'session': session,
            'league': league,
            'play_info': play_info,
            'game': game,
        }
        if len(play) == 2:
            event = play[1].b.text.replace('  ', ' ')
            play_info['full_description'] = event
            event = event.lower()
            if 'timeout' in event:
                event_type = 'timeout'
            elif 'start' in event or 'end' in event:
                event_type = 'clock'
            else:
                print event
                raise Exception('unknown 2 column event')
        elif len(play) > 2:
            if play[1].text == '&nbsp;':
                event = play[3]
                team = home_team
                home = True
                other_team = away_team
            else:
                event = play[1]
                team = away_team
                home = False
                other_team = home_team
            if event.b:
                event = event.b
            play_params.update({'team': team,
                                'other_team': other_team, 
                                'home': home})
            event = event.text.replace('  ', ' ')
            play_info['full_description'] = event
            event = event.lower()
            special_cases = ('excsess timeout techchnical', 
                            'excess timeout turnover', 
                            'delay of game techncial', 
                            'technical foul')
            special_turnovers = ('shot clock turnover', 
                                'turnover', 
                                'bad pass', 
                                '5 sec inbound turnover')            
            if event in special_cases:
                event_type = 'team_foul'
            elif event in special_turnovers:
                event_type = 'special_turnover'
            elif 'timeout' in event:
                event_type = 'timeout'
            elif 'enters the game for' in event:
                event_type = 'substitution'
            elif 'Jumpball' in event or 'vs.' in event:
                event_type = 'jumpball'
            elif 'steal' in event:
                event_type = 'steal'
            elif 'foul' in event:
                if 'draws' in event:
                    event_type = 'draw_foul'
                elif 'double' in event:
                    event_type = 'double_foul'
                elif 'illegal defense' in event or 'defensive' in event:
                    event_type = 'illegal_defense'
                elif 'off foul' in event:
                    event_type = 'off_turnover'
                else:
                    event_type = 'num_foul'
            elif 'turnover' in event:
                event_type = 'turnover'
            elif 'free throw' in event:
                event_type = 'free_throw'
            elif 'makes' in event or 'misses' in event:
                event_type = 'shot'
            elif 'blocks' in event:
                event_type = 'block'
            elif 'rebound' in event:
                event_type = 'rebound'
            elif 'eject' in event:
                event_type = 'ejection'
            elif 'illegal defense' in event:
                event_type = 'illegal_defense'
            else:
                event_type = 'violation'
            play_params.update({'event_type': event_type}) 
            play = process_play(**play_params) 
        
