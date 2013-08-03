import re
from pprint import pprint

def test_items(items, regex):    
    for item in items:
        event, result = item
        match = regex.match(event)
        if match:
            if not result == match.groups():
                pprint(event)
                print "expected", result
                print "matches", match.groups()
        else:
            print "regex doesn't work", event
            
def test_timeout():
    timeout = re.compile(
              r"(?P<team_identifier>\b.+?\b)? ?"
              "(?P<timeout_type>full|20 sec.|official)? ?"
              "(?:timeout)"
              "(?: called by )?"
              "(?P<player_name>.+)?")
    a = ["Oklahoma City 20 sec. timeout called by Jermaine O'Neal",
        ("Oklahoma City", "20 sec.", "Jermaine O'Neal")]
    b = ["Oklahoma City full timeout", 
        ("Oklahoma City", "full", None)]
    c = ["Oklahoma City 20 sec. timeout", 
        ("Oklahoma City", "20 sec.", None)]
    d = [" timeout", 
        (None, None, None)]
    e = [" full timeout", 
        (None, "full", None)]    
    f = ["Oklahoma 20 sec. timeout", 
        ("Oklahoma", "20 sec.", None)]
    g = ["official timeout", 
        ("official", None, None)]
    h = ["oklahoma city official timeout",
        ("oklahoma city", "official", None)]
    i = ["new york full timeout called by carmelo anthony",
        ("new york", "full", "carmelo anthony")]
    items = a, b, c, d, e, f, g, h, i
    test_items(items, timeout)
test_timeout()
    
def test_jumpball():
    jumpball = re.compile(
               "(?:Jumpball\: )?"
               "(?P<player_a>.+) vs\. (?P<player_b>.+) "
               "\((?P<possesor>.+) "
               "gains possession\)")
    a = ["Jumpball: Jermaine O'Neal vs. J.R. Smith (John Walker III gains possession)", 
        ("Jermaine O'Neal", "J.R. Smith", "John Walker III")]
    b = ["Jermaine O'Neal vs. J.R. Smith (John Walker III gains possession)", 
        ("Jermaine O'Neal", "J.R. Smith", "John Walker III")]
    items = a, b
    test_items(items, jumpball)

def test_substitution():
    substitution = re.compile(
                   "(?P<enters>.+?)? ?"
                   "enters the game for ? ?"
                   "(?P<leaves>.+)?")
    a = ["Jermaine O'Neal enters the game for J.R. Smith",
        ("Jermaine O'Neal", "J.R. Smith")]
    b = ["enters the game for chris quinn",
        (None, "chris quinn")]
    c = ["chris quinn enters the game for",
        ("chris quinn", None)]
    d = ["jan vesely enters the game for  nene",
        ("jan vesely", "nene")]   
    items = a, b, c, d
    test_items(items, substitution)
test_substitution()
    

def test_rebound():
    rebound = re.compile(
              " ?"
              "(?P<rebounder_name>.+?)? ?"
              "(?P<offensive>offensive|defensive) "
              "(?P<team>team)? ?"
              "rebound")
    a = ["Boston offensive team rebound", 
        ("Boston", "offensive", "team")]
    b = ["Jermaine O'Neal defensive rebound", 
        ("Jermaine O'Neal", "defensive", None)]
    c = ["Oklahoma City defensive team rebound", 
        ("Oklahoma City", "defensive", "team")]
    d = ["defensive team rebound", 
        (None, "defensive", "team")]
    e = [" defensive team rebound", 
        (None, "defensive", "team")]
    f = ["offensive team rebound",
        (None, "offensive", "team")]
    items = a, b, c, d, e, f
    test_items(items, rebound)
            
def test_violation():
    violation = re.compile(
                "(?P<player_name>.+?)? ?"
                "(?:(?:turnover|violation) ?: ?)?"
                "(?P<violation_type>kicked ball|bad pass|traveling|"
                "backcourt|defensive goaltending|lane|3 second|"
                "discontinue dribble|double dribble|"
                "offensive goaltending|delay of game|jump ball|"
                "inbound|lost ball|10 second|5 second|8 second|"
                "out of bounds|shot clock|illegal defense|"
                "travelling|violation) ?"
                "(?:violation)?")
    a = ["jermaine o'neal offensive goaltending violation", 
        ("jermaine o'neal", "offensive goaltending")]
    b = ["j.r. Smith offensive goaltending", 
        ("j.r. Smith", "offensive goaltending")]
    c = ["jermaine o'neal jump ball violation", 
        ("jermaine o'neal", "jump ball")]
    d = ["8 second", 
        (None, "8 second")]
    e = ["traveling", 
        (None, "traveling")]
    f = ["tyson chandler lane violation", 
        ("tyson chandler", "lane")]
    g = ["tyson chandler violation", 
        ("tyson chandler", "violation")]
    h = ["pistons turnover: shot clock violation", 
        ("pistons", "shot clock")]
    i = ["nikola pekovic turnover : offensive goaltending",
        ("nikola pekovic", "offensive goaltending")]
    j = ["andrei kirilenko violation:defensive goaltending",
        ("andrei kirilenko", "defensive goaltending")]
    k = ["delay of game violation",
        ("delay of game", "violation")]    
    items = a, b, c, d, e, f, g, h, i, j, k
    test_items(items, violation)
test_violation()

def test_steal():
    steal = re.compile(
            "(?P<turnerover_name>.+?) "
            "(?P<steal_type>bad pass|jump ball violation|"
            "lost ball|out of bounds lost ball|post lost ball)? ?"
            "(?:turnover )?"
            "\( ?(?P<stealer_name>.+) "
            "steals\)")
    a = ["Jermaine O'Neal lost ball (J.R. Smith steals)",
        ("Jermaine O'Neal", "lost ball", "J.R. Smith")]
    b = ["J.R. Smith jump ball violation (Jermaine O'Neal steals)",
        ("J.R. Smith", "jump ball violation", "Jermaine O'Neal")]
    c = ["Jermaine O'Neal lost ball turnover (J.R. Smith steals)",
        ("Jermaine O'Neal", "lost ball", "J.R. Smith")]
    d = ["J.R. Smith out of bounds lost ball turnover (Jermaine O'Neal steals)",
        ("J.R. Smith", "out of bounds lost ball", "Jermaine O'Neal")]
    e = ["paul pierce post lost ball turnover (norris cole steals)",
        ("paul pierce", "post lost ball", "norris cole")]
    f = ["anderson varejao turnover (luol deng steals)",
        ("anderson varejao", None, "luol deng")]
    items = a, b, c ,d, e, f
    test_items(items, steal)
test_steal()

def test_draw_foul():
    draw_foul = re.compile(
                "(?P<commits>.+?) "
                "(?P<foul_description>hanging on rim|"
                     "loose ball|shooting|inbound|clear path|"
                     "offensive|block|take|charge|flagrant|"
                     "away from ball|punching)? ?"
                "(?:personal)? ?"
                "(?:foul)? ? ?"
                "(?:type (?P<flagrant_type>[1,2]))? ?"
                "(?:take|charge|block|charging)? ?"
                "(?:foul)? ?"
                "\( ?(?P<draws>.+) draws the foul ?\)")
    a = ["Jermaine O'Neal shooting personal foul (J.R. Smith draws the foul)", 
        ("Jermaine O'Neal", "shooting", None, "J.R. Smith")]
    b = ["Jermaine O'Neal shooting personal foul (J.R. Smith draws the foul )", 
        ("Jermaine O'Neal", "shooting", None, "J.R. Smith")]
    c = ["Jermaine O'Neal personal foul (J.R. Smith draws the foul)", 
        ("Jermaine O'Neal", None, None, "J.R. Smith")]
    d = ["Jermaine O'Neal flagrant foul type 2 (J.R. Smith draws the foul)", 
        ("Jermaine O'Neal", "flagrant", "2", "J.R. Smith")]
    e = ["Jermaine O'Neal (J.R. Smith draws the foul )", 
        ("Jermaine O'Neal", None, None, "J.R. Smith")]
    f = ["Richard Jeff offensive charging foul (Ryan Hollins draws the foul )",
        ("Richard Jeff", "offensive", None, "Ryan Hollins")]
    g = ["Ronny Turiaf shooting foul ( Nene draws the foul)",
        ("Ronny Turiaf", "shooting", None, "Nene")]
    items = a, b, c, d, e, f, g
    test_items(items, draw_foul)
test_draw_foul()

def test_double_foul():
    double_foul = re.compile(
                  "[D,d]ouble "
                  "(?P<foul_type>personal|technical) "
                  "foul: "
                  "(?P<player_a>.+?) "
                  "(?:\([0-9]\) )?"
                  "and "
                  "(?P<player_b>[A-Z,a-z,\.,\',\s]+(?!\([0-9]\)))"
                  "(?:.+)?")
    a = ["Double personal foul: Jermaine O'Neal and J.R. Smith",
        ("personal", "Jermaine O'Neal", "J.R. Smith")]
    b = ["double technical foul: Jermaine O'Neal and J.R. Smith",
        ("technical", "Jermaine O'Neal", "J.R. Smith")]
    c = ["Double personal foul: Jermaine O'Neal (2) and Johnny Walker Jr. (5)",
        ("personal", "Jermaine O'Neal", "Johnny Walker Jr.")]
    d = ["double personal foul: kevin garnett (2) and lebron james (5) are each charged with a personal foul",
        ("personal", "kevin garnett", "lebron james")]
    items = a, b, c, d
    test_items(items, double_foul)
    double_foul = re.compile(
                  "(?P<player_name>.+) "
                  "double "
                  "(?P<foul_type>personal|technical) "
                  "foul")
    a = ["Jermaine O'Neal double personal foul",
        ("Jermaine O'Neal", "personal")]
    b = ["J.R. Smith double technical foul",
        ("J.R. Smith", "technical")]    
    items = a, b
    test_items(items, double_foul)
test_double_foul()
    
def test_illegal_defense():    
    illegal_defense = re.compile(
                   "(?P<violator_name>.+) "
                   "(?:illegal defense|defensive 3-seconds)"
                   "(?: foul| \(Technical Foul\))?")
    a = ["Jermaine O'Neal illegal defense foul",
        ("Jermaine O'Neal",)]
    b = ["J.R. Smith illegal defense",
        ("J.R. Smith",)]
    c = ["Chris Copeland defensive 3-seconds (Technical Foul)",
        ("Chris Copeland",)]
    items = a, b, c
    test_items(items, illegal_defense)
test_illegal_defense()

def test_off_turnover():
    off_turnover = re.compile(
                    "(?P<player_name>.+) "
                    "(?:off|offensive) "
                    "foul"
                    "(?: turnover)?")
    a = ["Jermaine O'Neal off foul turnover",
        ("Jermaine O'Neal",)]
    b = ["james harden offensive foul",
        ("james harden",)]
    items = a, b
    test_items(items, off_turnover)
test_off_turnover()

def test_num_foul():
    num_foul = re.compile(
               "(?P<commits>.+?) "
               "(?:team )?"
               "(?:foul )?"
               "(?P<foul_extra>taunting|non-unsportsmanlike)? ?"
               "(?P<foul_description>loose ball|offensive|technical|"
                        "hanging on rim|shooting|personal|foul) "
               "(?:foul)? ?"
               "(?:\([0-9]{0,2}[a-z]{2} "
               "(?P<foul_type>personal|technical) "
               "foul\))?")
    a = ["Jermaine O'Neal taunting personal foul (5th personal foul)",
        ("Jermaine O'Neal", "taunting", "personal", "personal")]
    b = ["J.R. Smith hanging on rim foul (4th technical foul)",
        ("J.R. Smith", None, "hanging on rim", "technical")]
    c = ["Johnny Walker Jr. loose ball foul (3rd personal foul)",
        ("Johnny Walker Jr.", None, "loose ball", "personal")]
    d = ["Carmelo Anthony technical foul(1st technical foul)",
        ("Carmelo Anthony", None, "technical", "technical")]
    e = ["Omer Asik personal foul",
        ("Omer Asik", None, "personal", None)]
    f = ["oklahoma city team technical foul",
        ("oklahoma city", None, "technical", None)]
    g = ["lebron james foul (1st personal foul)",
        ("lebron james", None, "foul", "personal")]
    items = a, b, c, d, e, f, g
    test_items(items, num_foul)
test_num_foul()

def test_turnover():
    turnover = re.compile(
           "(?P<player_name>.+?) "
           "(?P<violation_type>double personal|palming|"
                    "out of bounds lost ball|step out of bounds|"
                    "post lost ball|illegal screen|illegal assist|"
                    "basket from elbows|steps out of bounds|bad pass|"
                    "opposite basket|swinging elbows)? ?"
           "turnover")
    a = ["Jermaine O'Neal double personal turnover",
        ("Jermaine O'Neal", "double personal")]
    b = ["Johnny Walker III basket from elbows turnover",
        ("Johnny Walker III", "basket from elbows")]
    c = ["team turnover",
        ("team", None)]
    d = ["Kevin Garnett opposite basket turnover",
        ("Kevin Garnett", "opposite basket")]
    items = a,  b, c, d
    test_items(items, turnover)
test_turnover()

def test_free_throw():
    free_throw = re.compile(
                 "(?P<shooter_name>.+) "
                 "(?P<makes>misses|makes) "
                 "(?P<adjective>technical|flagrant)? ?"
                 "free throw ?"
                 "(?:[1-3] of [1-3])?")
    a = ["Jermaine O'Neal makes technical free throw",
        ("Jermaine O'Neal", "makes", "technical")]
    b = ["J.R. Smith misses free throw",
        ("J.R. Smith", "misses", None)]
    c = ["Johnny Walker Jr. makes free throw 1 of 2",
        ("Johnny Walker Jr.", "makes", None)]
    d = ["Nene makes flagrant free throw 1 of 2",
        ("Nene", "makes", "flagrant")]
    items = a, b, c, d
    test_items(items, free_throw)

def test_shot():
    shot = re.compile(
       "(?P<shooter_name>.+) "
       "(?P<result>makes|misses) ?"
       "(?:(?P<length>[0-9]{1,2})-foot)? ?"
       "(?P<adjective>.+?)? "
       "(?P<shot_type>shot|jumper|dunk|layup|pointer) ?"
       "(?:\( ?(?P<assistant_name>.+?) assists\))?")
    a = ["Jermaine O'Neal makes 20-foot jumper",
        ("Jermaine O'Neal", "makes", "20", None, "jumper", None)]
    b = ["J.R. Smith makes amazingly spectacular dunk (Jermaine O'Neal assists)",
        ("J.R. Smith", "makes", None, "amazingly spectacular", 
        "dunk", "Jermaine O'Neal")]
    c = ["Johnny Walker Jr. misses 2-foot dunk (Jermaine O'Neal assists)",
        ("Johnny Walker Jr.", "misses", "2", None, "dunk", "Jermaine O'Neal")]
    d = ["Johnny Walker Jr. makes jumper (Jermaine O'Neal assists)",
        ("Johnny Walker Jr.", "makes", None, None, "jumper", "Jermaine O'Neal")]
    e = ["Johnny Walker Jr. misses running dunk (Jermaine O'Neal assists)",
        ("Johnny Walker Jr.", "misses", None, "running", "dunk", "Jermaine O'Neal")]
    f = ['maurice evans makes 21-foot two point shot ( nene assists)',
        ('maurice evans', 'makes', '21', 'two point', 'shot', 'nene')]
    items = a, b, c, d, e, f
    test_items(items, shot)
    shot = re.compile(
       "(?P<shooter_name>.+) "
       "(?P<result>makes|misses) ?"
       "(?:(?P<length>[0-9]{1,2})- foot)?")
    f = ["Emeka Okafor misses 5- foot",
        ("Emeka Okafor", "misses", "5")]
    g = ["James Harden misses",
        ("James Harden", "misses", None)]
    items = f, g
    test_items(items, shot)
test_shot()
    
def test_block():
    block = re.compile(
            "(?P<blocker_name>.+) "
            "blocks "
            "(?P<shooter_name>.+)'s "
            "(?:(?P<length>[0-9]+)-foot)? ?"
            "(?P<adjective>.+?)? ?"
            "(?P<shot_type>shot|jumper|dunk|layup|three pointer)")
    a = ["Jermaine O'Neal blocks J.R. Smith's 20-foot running jumper",
        ("Jermaine O'Neal", "J.R. Smith", "20", "running", "jumper")]
    b = ["Jermaine O'Neal blocks Johnny Walker Jr.'s running layup",
        ("Jermaine O'Neal", "Johnny Walker Jr.", None, "running", "layup")]
    c = ["Jermaine O'Neal blocks Johnny Walker Jr.'s 2-foot layup",
        ("Jermaine O'Neal", "Johnny Walker Jr.", "2", None, "layup")]
    d = ["Jermaine O'Neal blocks J.R. Smith's 20-foot running three pointer",
        ("Jermaine O'Neal", "J.R. Smith", "20", "running", "three pointer")]
    e = ["Jermaine O'Neal blocks J.R. Smith's three pointer",
        ("Jermaine O'Neal", "J.R. Smith", None, None, "three pointer")]
    items = a, b, c, d, e
    test_items(items, block)

def test_ejection():    
    ejection = re.compile(
               "(?P<player_name>.+) "
               "ejected")
    a = ["Jermaine O'Neal ejected",
        ("Jermaine O'Neal",)]
    b = ["J.R. Smith ejected",
        ("J.R. Smith",)]
    items = a, b
    test_items(items, ejection)



                    
