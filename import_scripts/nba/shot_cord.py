import urllib2
import urllib
import math
import csv
import datetime
import time
import string
import re
import warnings
from pprint import pprint
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from connect_db import *
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.play_by_play import *
from helpers import *

def import_shots():
    session = create_session(True)
    league = session.query(League).filter_by(abbr='nba').one()
    bad_game_ids = ['400400517', '400400488', '400400474', '400400472', 
                    '400400471', '400400466', '400400464', '400400463', 
                    '400400462', '400400461', '310111001', '301102018',
                    '301022014', '301016024', '301016005', '301014029',
                    '301014025', '301012014', '301007138', '301003143', 
                    '301003017', '300206027', '291020012', '291018018',
                    '291012005',]
    all_star_games = ['320226031', '310220032', '300214032']
    need_to_get_to_later = ['320404012', '320314017', '320312017', '320310017', 
                            '320309030', '320307017', '320306013', '320304030']
    external_game_ids = session.query(GameExternalID)\
                               .filter(GameExternalID.shot_cords==False,
                                       GameExternalID.pbp==True,
                                       GameExternalID.league_id==league.id)\
                               .filter(not_(GameExternalID\
                                                 .external_id\
                                                 .in_(bad_game_ids)))\
                               .filter(not_(GameExternalID\
                                                 .external_id\
                                                 .in_(all_star_games)))\
                               .order_by(desc(GameExternalID.external_id))
    for external_game_id in external_game_ids:
        print external_game_id
        done = import_shot_cord(external_game_id)
        external_game_id.shot_cords=True
        session.add(external_game_id)
        session.commit()
            
def import_shot_cord(external_game_id):
    session = create_session()
    league = session.query(League).get(2)
    bad_ids = ['32010202100320', '32010202100321', '400400559224',
               '400400548150', '400400548148', '400400544204']
    source_name = 'espn'
    shot_url = 'http://sports.espn.go.com/nba/gamepackage/data/shot?gameId=%s'
    shot_url %= external_game_id.external_id
    shot_xml = urllib2.urlopen(shot_url)
    body = BeautifulStoneSoup(shot_xml)
    shots = body.findAll('shot')
    game = external_game_id.game
    external_id = external_game_id.external_id
    for num, shot in enumerate(shots):
        if not shot['id'] in bad_ids:
            shooter_name = shot['p'].replace('  ', ' ')
            away_or_home = shot['t']
            if away_or_home == 'a':
                team = game.away_team
            else:
                team = game.home_team
            period = int(shot['qtr'])
            description = shot['d']
            shot_info = re.compile(
                        "(?P<make>Made|Miss) "
                        "(?P<length>[0-9]{0,2})ft "
                        "(?P<shot_type>jumper|3-pointer) "
                        "(?P<time_of_game>[0-9]{0,2}:[0-9]{0,2}) in "
                        "(?P<period>[0-4])(?:st|th|rd|nd) "
                        "(?P<period_type>Qtr.|OT)")
            match = shot_info.match(description)
            (make, length, shot_type, 
             time_of_game, period, period_type) = match.groups()
            if shot['made'] == "true":
                make = True
            else:
                make = False
            period = int(period)
            length = int(length)
            x = int(shot['x'])
            y = int(shot['y'])
            external_shot_id = shot['id'][len(external_id):]
            shot_id_match = '%s%s' % (external_id, external_shot_id)
            if not shot['id'] == shot_id_match:
                raise Exception('external shot id mismatch') 
            if period_type == 'OT':
                period += 4
            time_of_game = datetime.datetime\
                                   .strptime(time_of_game, '%H:%M').time()
            shot_info = {
                'game_id': game.id,
                'period': period,
                'time_of_game': time_of_game,
                'make': make
            }
            try:
                player_external_id = str(int(shot['pid']))
            except ValueError:
                if not shot['pid'] and not shot['p']:
                    shot, c = get_or_create(session, Shot, **shot_info)
                    shot_cords, c = get_or_create(session, 
                                ShotCoordinates, 
                                shot_id=shot.id, 
                                external_shot_id=external_shot_id, 
                                length=length, 
                                x=x, y=y,
                                shot_type=shot_type)
                    continue
            if shot['id'] == '400400552535':
                shooter_name = 'Charles Jenkins'
                player_external_id = '6444'
                shot_info['make'] = True
            if shot['id'] == '400400548148':
                shot_info['make'] = True
            shooter = get_player(session, league.id, shooter_name, team)
            if shooter:
                shot_info.update({'shooter_id': shooter.id})
            else:
                if shot['p']:
                    if player_external_id == '1713':
                        shooter_name = 'Nene Hilario'
                        shooter = get_player(session, league.id, 
                                             shooter_name, team)
                    else:
                        print shot['p']
                        raise Exception('player not found')
            try:
                player = session.query(Player)\
                    .join(PlayerExternalID)\
                    .filter(Player.league_id==league.id, 
                            PlayerExternalID.external_id==player_external_id)\
                    .one()
            except NoResultFound:
                print shooter_name
                print player_external_id
                raise Exception('no player found for this external id')
            except MultipleResultsFound:
                print shooter_name
                print player_external_id
                raise Exception('too many players found for this id')
            if not shooter == player:
                print shooter
                print player
                print player_external_id
                raise Exception('player mismatch')
            try:
                shots = session.query(Shot)\
                               .filter(not_(Shot.shot_type=='free throw'))\
                               .filter_by(**shot_info)
                shot = shots.one()
            except NoResultFound:
                num_plays = session.query(Clock)\
                                   .filter_by(game_id=game.id)\
                                   .count()
                if num_plays == 0:
                    shot_info.update({
                                    'shot_type': shot_type,
                                    'length': length})
                    shot = Shot(**shot_info)
                    save(session, shot)
                else:
                    try:
                        shot = session.query(Shot)\
                                      .filter_by(**shot_info).all()
                        if shot: 
                            if(shot[0].shot_type == 'free throw' 
                               and shot_type == 'jumper'
                               and length == 8):
                                continue
                        else:
                            print shot
                            print shot_info
                            print description
                            raise Exception('i dunno anymore')
                    except NoResultFound:
                        print shot_info
                        print description
                        print game.id
                        print shooter.id
                        raise Exception('shot not found')
            except MultipleResultsFound:
                shots = shots.all()
                if not shots[0].shot_coordinates:
                    shot = shots[0]
                elif not shots[1].shot_coordinates:
                    shot = shots[1]
                elif len(shots) == 3 and not shots[2].shot_coordinates:
                    shot = shots[2]                      
                else:
                    good = True
                    for shot in shots:
                        if not shot.shot_coordinates:
                            good = False
                    if not good:
                        print shots
                        print shot_info
                        print description
                        raise Exception('too many shots' 
                                        'found')
                    else:
                        continue                                   
            shot_cords, cc = get_or_create(session, ShotCoordinates, 
                                            shot_id=shot.id, 
                                            external_shot_id=external_shot_id, 
                                            length=length, 
                                            x=x, y=y,
                                            shot_type=shot_type)
    return True
                               
