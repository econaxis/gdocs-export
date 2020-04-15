import pyodbc
import pickle
import threading
import secrets
from datetime import datetime
import sqlalchemy as sal
from sqlalchemy import create_engine, MetaData, Column, Integer, String, Table, DateTime, ForeignKey 
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import pprint
import urllib
import os

SQLPASS = os.environ["SQL_PASS"]

cr = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pydoc-db.database.windows.net,1433;Database=pydoc-db;Uid=henry2833;Pwd={%s};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"%SQLPASS

params = urllib.parse.quote_plus(cr)

engine = sal.create_engine("mssql+pyodbc:///?odbc_connect=%s"%params, pool_size = 30, echo = True,
        max_overflow = 300)

#engine = sal.create_engine('sqlite+pysqlite:///test.db', echo = True)
conn = engine.connect()

meta = MetaData(bind = engine)

_session = sessionmaker(bind=engine)
sess = _session()
Base = declarative_base()

class Files(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key = True)

    fileName = Column(String(120))
    fileId = Column(String(120), unique = True)

    lastModDate = Column(DateTime)
    parent_id = Column(String(120), ForeignKey('owner.name'))
    parent = relationship("Owner", back_populates = "children")

    children = relationship("Dates", back_populates = "parent")

    def __repr__(self):
        return f"Files\n"

class Owner(Base):
    __tablename__ = "owner"
    id = Column(Integer, primary_key = True)
    name = Column(String(120), unique = True)
    children = relationship("Files", back_populates = "parent")
    def __repr__(self):
        return f"Owner \n"

class Dates(Base):
    __tablename__ = "dates"
    id = Column(Integer, primary_key = True)
    parent_id = Column(String(120), ForeignKey('files.fileId'))
    moddate = Column(DateTime)

    parent = relationship("Files", back_populates = "children")

    def __repr__(self):
        return f"Date \n"

Base.metadata.create_all(engine)

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
            fileArr=[dict(fileName =i, fileId = fileId,
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
    print("sql start, received ", userid, workingPath)
    q= sess.query(Owner).filter(Owner.name == userid).count()
    if not q:
        ins = Owner.__table__.insert().values(name = userid)
        conn.execute(ins)

    df = pickle.load(open(workingPath + 'collapsedFiles_p.pickle', 'rb'))

    filesList = df.index.levels[0]
    ts = []

    step = 30
    print(len(filesList))
    for i in range(0, len(filesList),step ):
        print("ds")
        curses = scoped_session(_session)
        ds = mt(i, i+step, curses, df, userid)
        ts.append(ds)
    for i in ts:
        i.start()

    for i in ts:
        i.join()


if __name__ == '__main__':

   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()
    
    start("testing", "")



    print('aaa'*100)



