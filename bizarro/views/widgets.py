def articles_widget(request):
    filters = request.matchdict
    session = create_session()
    articles = session.query(Article)\
                      .join(MediaItemLeague, League)
    if filters.has_key('sport'):
        articles = articles.filter(League.sport_name==sport)
    if filters.has_key('league_abbr'):
        articles = articles.filter(Leauge.abbr==league_abbr)
    if filters.has_key('team_id'):
        pass
    if filter.has_key('person_name'):
        pass
    if filter.has_key('keywords'):
        pass
    articles = []
    return articles

def twitter_widget(request):
    filters = request.matchdict
    session = create_session()
    articles = session.query(Article)\
                      .join(MediaItemLeague, League)
    if filters.has_key('sport'):
        articles = articles.filter(League.sport_name==sport)
    if filters.has_key('league_abbr'):
        articles = articles.filter(Leauge.abbr==league_abbr)
    if filters.has_key('team_id'):
        pass
    if filter.has_key('person_name'):
        pass
    if filter.has_key('keywords'):
        pass
    twitters = []
    return twitters

def video_widget(request):
    filters = request.matchdict
    session = create_session()
    articles = session.query(Article)\
                      .join(MediaItemLeague, League)
    if filters.has_key('sport'):
        articles = articles.filter(League.sport_name==sport)
    if filters.has_key('league_abbr'):
        articles = articles.filter(Leauge.abbr==league_abbr)
    if filters.has_key('team_id'):
        pass
    if filter.has_key('person_name'):
        pass
    if filter.has_key('keywords'):
        pass
    videos = []
    return videos

        
