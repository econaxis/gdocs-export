from processing.sql import *
from sqlalchemy.orm import *
from sqlalchemy.sql import *
from processing.models import *


Base = declarative_base()


userid ="04e16af4-3c6a-4f6b-babd-612651d5e901"

sq = sess.query(Dates.parent_id, func.count('*').label('count')).group_by(Dates.parent_id).subquery()
act = sess.query(Files.fileName, sq.c.count).filter(Files.parent_id==userid).join(sq).all()

activities = {}
activities["time"]= [x[1] for x in act]
activities["files"] = [x[0] for x in act]
print(activities)
