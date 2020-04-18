import sys
import pickle
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
import pprint
import os

from processing.models import Owner, Files, Closure, Dates, Base


PARAMS = os.environ["SQL_CONN"]

engine = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s"%PARAMS, pool_size = 30, echo = True,
        max_overflow = 300)

Base.metadata.create_all(bind=engine)

#engine = sqlal.create_engine('sqlite+pysqlite:///test.db', echo = True)
CONN = engine.connect()

meta = MetaData(bind = engine)

_session = sessionmaker(bind=engine)
sess = _session()
scoped_sess = scoped_session(_session)

class mt (threading.Thread):
    def __init__(self, ind, end, session, df, userid):
        super(mt, self).__init__()
        self.ind = ind
        self.userid = userid
        self.end = end
        self.session = session
        self.df = df
    def run(self):
        df = self.df
        filesList = df.index.levels[0]
        objects = []
        for counter, i in enumerate(filesList[self.ind:self.end]):
            timesList = df.loc[i].index.to_pydatetime()
            fileId = secrets.token_urlsafe(8)
            fileArr=[dict(fileName =i[0:119], fileId = fileId,
                lastModDate = max(timesList), parent_id =self.userid)]

            self.session.bulk_insert_mappings(Files, fileArr)
            self.session.commit()
            for k in timesList:
                objects.append(dict(parent_id =fileId, moddate = k))

        self.session.bulk_insert_mappings(Dates, objects)
        print(self.ind)
        self.session.commit()
        objects = []

#Create default owner

def start(userid, workingPath):
    q= sess.query(Owner).filter(Owner.name == userid).count()
    if not q:
        ins = Owner.__table__.insert().values(name = userid)
        CONN.execute(ins)

    df = pickle.load(open(workingPath + 'collapsedFiles_p.pickle', 'rb'))

    filesList = df.index.levels[0]
    ts = []

    step = 30
    print(len(filesList))
    for i in range(0, len(filesList),step ):
        curses = scoped_session(_session)
        ds = mt(i, i+step, curses, df, userid)
        ts.append(ds)

    for i in ts:
        i.start()

    for i in ts:
        i.join()

    closure = []
    df = pickle.load(open(workingPath + 'closure.pickle', 'rb'))


    for c in df:
        c = list(c)
        closure.append(dict(parent=c[0], child = c[1], owner_id = userid, depth = c[2]))

    try:
        sess.bulk_insert_mappings(Closure, closure)
        sess.commit()
    except:
        e = sys.exc_info()[0]
        print(str(e))

def main():
   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()
    


    wpath = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
    start("testing", wpath)

    print('aaa'*100)



