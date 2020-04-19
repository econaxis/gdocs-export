import sys
from queue import Queue
import pickle
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
import pprint
import os

from processing.models import Owner, Files, Closure, Dates, Base, Filename


PARAMS = os.environ["SQL_CONN"]

ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=30, echo=True,
                             max_overflow=300)

Base.metadata.create_all(bind=ENGINE)

#engine = sqlal.create_engine('sqlite+pysqlite:///test.db', echo = True)
CONN = ENGINE.connect()

_session = sessionmaker(bind=ENGINE)
sess = _session()
scoped_sess = scoped_session(_session)


def commit(q, sess, _type):
    _temp = []
    counter = 0
    while (not q.empty()):
        counter += 1
        _temp.append(q.get_nowait())
        if (counter % 300 == 0):
            print("SIZE: ", q.qsize())
            sess.bulk_insert_mappings(_type, _temp)
            sess.commit()
            _temp = []

    sess.bulk_insert_mappings(_type, _temp)
    sess.commit()


def start(userid, path):
    sess.add(Owner(name=userid))
    sess.commit()

    files = pickle.load(open(path + 'pathedFiles.pickle', 'rb'))
    clos = pickle.load(open(path + 'closure.pickle', 'rb'))
    idmapper = pickle.load(open(path + 'idmapper.pickle', 'rb'))


    lt_files = Queue()
    lt_dates = Queue()
    lt_closure = Queue()
    lt_filenames = Queue()

    for f in files:
        fileId = f[-1]
        print(fileId)
        print(idmapper[fileId])
        lt_files.put(dict(fileId=fileId, fileName=idmapper[fileId]))
        for d in files[f]:
            lt_dates.put(dict(fileId=fileId, moddate=d, owner_id = userid))

    for c in clos:
        lt_closure.put(
            dict(
                parent=c[0],
                child=c[1],
                depth=c[2],
                owner_id=userid))

    for n in idmapper:
        lt_filenames.put(dict(fileId = n, fileName = idmapper[n], owner_id = userid))

    tdManage = []
    thread_count = 50

    for i in range(thread_count):
        scoped_sess = scoped_session(_session)

        x = threading.Thread(
            target=commit, args=(
                lt_files, scoped_sess, Files))
        tdManage.append(x)
        x.start()

    for i in range(thread_count):
        scoped_sess = scoped_session(_session)

        x = threading.Thread(
            target=commit, args=(
                lt_dates, scoped_sess, Dates))
        tdManage.append(x)
        x.start()
    for i in range(thread_count):
        scoped_sess = scoped_session(_session)
        scoped_sess1 = scoped_session(_session)

        x = threading.Thread( target=commit, args=( lt_closure, scoped_sess, Closure))
        x1 = threading.Thread( target=commit, args=( lt_filenames, scoped_sess1, Filename))

        tdManage.append(x)
        tdManage.append(x1)
        x1.start()
        x.start()

    for x in tdManage:
        print("donse")
        x.join()


    print("userid: ", userid)

if __name__ == '__main__':
   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()

    from datetime import datetime
    wpath = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
    start("testing" + datetime.now().__str__(), wpath)
