import pickle
import sqlalchemy as sal
from sqlalchemy import Column, Integer, MetaData, PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib

cr = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pydoc-db.database.windows.net,1433;Database=pydoc-db;Uid=henry2833;Pwd={Infoip32};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
params = urllib.parse.quote_plus(cr)

engine = sal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % params, pool_size=500,
                           max_overflow=30, echo=True)

#engine = sal.create_engine('sqlite+pysqlite:///test.db', echo = True)
conn = engine.connect()

meta = MetaData(bind=engine)

_session = sessionmaker(bind=engine)
sess = _session()
Base = declarative_base()


class Pck(Base):
    __tablename__ = "pck"
    id = Column(Integer, primary_key=True)
    creds = Column(PickleType)

    def __repr__(self):
        return f"ds \n"


Base.metadata.create_all(engine)


if __name__ == '__main__':

   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()

    creds = pickle.load(open('creds.pickle', 'rb'))
    nw = Pck(creds=creds)
    sess.add(nw)
    sess.commit()

    print('aaa' * 100)
