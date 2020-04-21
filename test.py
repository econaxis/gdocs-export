from sqlalchemy.sql import *
from processing.sql import *
from processing.models import *
from datetime import datetime
from datetime import timedelta


begindate = datetime(2010, month=5, day = 6, hour=12)


i=20
ftable = Files.__table__
dtable=Dates.__table__
q=select([literal_column("floor((datediff(second, '2010-05-06 12:00:00', moddate))/10000)*10000").label("bins"),ftable.c.id]) \
    .select_from(dtable.join(ftable).join(Owner.__table__)).where(Owner.__table__.c.id==i).alias()

q=select([literal_column("floor((datediff(second, '2010-05-06 12:00:00', moddate))/10000)*10000").label("bins"),ftable.c.id]) \
    .select_from(dtable.join(ftable).join(Owner.__table__)).alias()

q1 = select([q.c.bins, func.count('*')]).select_from(q).group_by(q.c.bins).order_by(q.c.bins)

d={}

for c in range(1, 5):
    print(c)
    print(d)
    d[c] = 0
    for i in range(20):
        s = time.time()
        if(c==4):
            CONN.execution_options(stream_results = True).execute(q1).fetchall()
        else:
            CONN.execution_options(stream_results = True).execute(q1.limit(c*20)).fetchall()
        d[c] +=time.time() -s


print(d)

res = CONN.execute(q1).fetchall()


print(res1)
