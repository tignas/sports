import sys

if __name__ == '__main__':
    if len(sys.argv) == 4:
        a, command, league, source_name = sys.argv
    elif len(sys.argv) == 3:
        a, command, league = sys.argv    
    elif len(sys.argv) == 2:
        a, command = sys.argv
    else:
        command = None
    
    if command == 'import_roster':
        from import_scripts.players import *
        import_roster(league)
    elif command == 'game_ids':
        from import_scripts.games import game_ids
        game_ids(league)
    elif command == 'import_boxscores':
        from import_scripts.games import import_boxscores
        import_boxscores(league)
    elif command == 'assign_game_type':
        from import_scripts.games import assign_game_type
        assign_game_type(league)
    elif command == 'boxscore_game_id':
        from import_scripts.games import boxscore_game_id
        boxscore_game_id(league)
    elif command == 'import_shot_cords':
        from import_scripts.shot_cord import import_shots
        import_shots()
    elif command == 'import_projections':
        from import_scripts.fantasy import import_projections
        import_projections(league)
    elif command == 'import_kickers':
        from import_scripts.fantasy import import_kickers
        import_kickers(league, source_name)
    elif command == 'import_defense':
        from import_scripts.fantasy import import_defense
        import_defense(league, source_name)
    elif command == 'flatten_stats':
        from import_scripts.games import flatten_stats
        flatten_stats(league)
    elif command == 'assign_defensive_stats':
        from import_scripts.games import assign_defensive_stats
        assign_defensive_stats()
    elif command == 'create_feeds':
        from import_scripts.sources import create_feeds
        create_feeds()
    elif command == 'create_sources':
        from import_scripts.sources import create_sources
        create_sources()
    elif command == 'assign_weeks':
        from import_scripts.games import assign_game_weeks
        assign_game_weeks()
    else:
        raise Exception('unknown command')
