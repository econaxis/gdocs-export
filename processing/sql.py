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
import logging

from processing.models import Owner, Files, Closure, Dates, Base, Filename


PARAMS = os.environ["SQL_CONN"]
print(PARAMS)
logging.debug(PARAMS)

ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=30, echo = False, max_overflow=300)

logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

Base.metadata.create_all(bind=ENGINE)

#engine = sqlal.create_engine('sqlite+pysqlite:///test.db', echo = True)
CONN = ENGINE.connect()

_session = sessionmaker(bind=ENGINE, autoflush=True)
sess = _session()
scoped_sess = scoped_session(_session)

def commit(q, sess, _type):
    _temp = []
    counter = 0
    while (not q.empty()):
        counter += 1
        _temp.append(q.get_nowait())
        if (counter % 50 == 0):
            print("SIZE: ", q.qsize())
            sess.bulk_insert_mappings(_type, _temp)
            sess.commit()
            _temp = []
    sess.bulk_insert_mappings(_type, _temp)
    sess.commit()



def adder(queue, sess):
    while(not queue.empty()):
        sess.add(queue.get_nowait())
def start(userid, path):
    owner = Owner(name=userid + datetime.now().strftime("%m/%d %h:%m%s"))
    sess.add(owner)
    sess.flush()

    files = pickle.load(open(path + 'pathedFiles.pickle', 'rb'))
    clos = pickle.load(open(path + 'closure.pickle', 'rb'))
    idmapper = pickle.load(open(path + 'idmapper.pickle', 'rb'))


    lt_files = Queue()
    lt_dates = Queue()
    lt_closure = Queue()
    lt_filenames = Queue()


    #fileid_obj_map maps gdrive fileids to file objects defined in models
    fileid_obj_map = {}

    for f in files:
        fileId = f[-1]
        file_obj = Files(fileId = fileId +datetime.now().strftime("%m/%d %h:%m:%s"), 
                lastModDate = files[f][0], owner = owner, isFile = True)

        fileid_obj_map[fileId] = file_obj

        lt_files.put(file_obj)

    adder(lt_files, sess)
    sess.flush()


    for f in files:
        fileid = f[-1]
        file_obj = fileid_obj_map[fileid]
        for d in files[f]:
            fileid = file_obj.id
            lt_dates.put(dict(moddate = d, fileId = fileid))


    tdManage = []
    for i in range(100):
        scoped_sess = scoped_session(_session)
        x = threading.Thread(
            target=commit, args=(
                lt_dates, scoped_sess, Dates))
        tdManage.append(x)
        x.start()



    for c in clos:
        try:
            file_obj = fileid_obj_map[c[0]]
        except:
            file_obj = Files(fileId = c[0], lastModDate = None, owner = owner, isFile = False)
            fileid_obj_map[c[0]] = file_obj
            lt_files.put(file_obj)
        lt_closure.put(Closure(parent_relationship = file_obj, files_relationship = fileid_obj_map[c[1]], owner = owner, depth = c[2]))


    for n in idmapper:
        try:
            file_obj = fileid_obj_map[n]
        except:
            #Folder type
            file_obj = Files(fileId = n, lastModDate = None, owner = owner, isFile = False)
            fileid_obj_map[n] = file_obj
            lt_files.put(file_obj)

        lt_filenames.put(Filename(fileName = idmapper[n], files = file_obj, owner = owner))


    adder(lt_filenames, sess)
    sess.flush()
    adder(lt_closure, sess)

    for i in tdManage:
        i.join()

    sess.commit()

    return




    for i in range(thread_count):
        scoped_sess = scoped_session(_session)

        x = threading.Thread(
            target=commit, args=(
                lt_files, scoped_sess, Files))
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
