import json
from itertools import groupby
from pyramid.view import view_config
from sqlalchemy.orm import aliased, eagerload
from sqlalchemy import and_, or_, desc, func
from bizarro.models.teams import *
from bizarro.models.people import *
from bizarro.models.stats import *
from bizarro.models.play_by_play import *

