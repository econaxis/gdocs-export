import random
from datetime import datetime
import sys
from queue import Queue
import pickle
import time
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
import pprint
from pprint import pformat
import os
import logging
from logging import FileHandler
import configlog
from processing.models import Owner, Files, Closure, Dates, Base, Filename


PARAMS = os.environ["SQL_CONN"]

logging.debug(PARAMS)

ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=5, echo = False, max_overflow=300)
#ENGINE = sqlal.create_engine('sqlite+pysqlite:///test.db', echo = True)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=ENGINE)

CONN = ENGINE.connect()

_session = sessionmaker(bind=ENGINE, autoflush=True)
sess = _session()
scoped_sess = scoped_session(_session)

def commit(q, sess, _type = None, add = False):
    logger.info("process begin sleep")
    _temp = []
    counter = 0
    iters = round(q.qsize() / 10000)
    iters = max(iters, 70)
    logger.info("iters: %d, len: %d", iters, q.qsize())
    while (q.qsize()):
        counter +=1
        try:
            _temp.append(q.get_nowait())
        except:
            break

        if (counter % iters == 0):
            time.sleep(random.uniform(0, 1))
            logger.info("flushing, len: %d", q.qsize())
            if(add):
                sess.bulk_save_objects(_temp)
            else:
                sess.bulk_insert_mappings(_type, _temp)

            logger.info("committing")
            sess.commit()
            _temp = []
            logger.info("done flushing")


    logger.info("while loop done")

    if(add):
        sess.bulk_save_objects(_temp)
    else:
        sess.bulk_insert_mappings(_type, _temp)

    sess.commit()
    logger.debug("commit func done")



def adder(queue, sess):
    counter = 0

    for i in queue:
        counter+=1
        sess.add(i)
        if(counter%90==0):
            logger.info("rem %d/%d", counter, len(queue))
            sess.flush()

    logger.info("committing")
    sess.commit()
    return
    while(not queue.empty()):
        counter +=1
        sess.add(queue.get_nowait())
        if(counter %50 == 0):
            sess.flush()
    sess.flush()

def start(userid, path):
    logger.info("STARTING SQL %s %s", userid, path)
    import secrets
    scrt = secrets.token_urlsafe(7)
    temp = name=userid[0:15] + datetime.now().strftime("%m %d %h") + scrt
    token = datetime.now().strftime("%d-%H.%f") + scrt
    owner = Owner(name=temp[0:39])
    sess.add(owner)
    sess.commit()

    logger.info("Added owner row, name: %s id: %s", owner.name, owner.id)

    files = {}

    names = pickle.load(open(path+'pickleIndex', 'rb'))
    for n in names:
        files.update(pickle.load(open(n, 'rb')))



    clos = pickle.load(open(path + 'closure.pickle', 'rb'))
    idmapper = pickle.load(open(path + 'idmapper.pickle', 'rb'))

    logger.info("Finished loading pickles")


    lt_files = []
    lt_dates = Queue()
    lt_closure = []
    lt_filenames = []


    tdManage = []

    #fileid_obj_map maps gdrive fileids to file objects defined in models
    fileid_obj_map = {}

    for f in files:
        fileId = f[-1]
        logger.warning("File: %s", fileId)
        if(fileId in fileid_obj_map):
            logger.warning("duplicaed fileid found, skipping")
            continue

        if(files[f]):
            last_mod = files[f][0]
        else:
            last_mod = None

        file_obj = Files(fileId = fileId + ":"+token,
                lastModDate = last_mod, owner = owner, isFile = True)

        fileid_obj_map[fileId] = file_obj

        lt_files.append(file_obj)

    #logger.debug("len of id map %d len of q %d", len(fileid_obj_map), lt_files.qsize())

   # sess.bulk_save_objects(lt_files)


    logger.info("starting bulk save")
    adder(lt_files, sess)
    logger.info("bulked save done")
    
    '''
    for i in range(25):
        scoped_sess = scoped_session(_session)
        x = threading.Thread(
            target=commit, args=(
                lt_files, scoped_sess, Files,  True))
        tdManage.append(x)
        x.start()
        logger.debug('starting new thread')

    for i in tdManage:
        logger.debug("joining")
        i.join()
    
    logger.debug('joining done')
    tdManage = []
    '''

    sess.flush()

    for i in lt_files:
        print(i.id)

    logger.info('sess flush done')

    for f in files:
        gdriveid = f[-1]
        file_obj = fileid_obj_map[gdriveid]

        for d in files[f]:
            fileid = file_obj.id
            lt_dates.put(dict(moddate = d, fileId = fileid))

    logger.info('starting thread for dates')


    for i in range(30):
        time.sleep(random.uniform(0, 10))
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
            file_obj = Files(fileId = c[0] + ":" + token, lastModDate = None, owner = owner, isFile = False)
            fileid_obj_map[c[0]] = file_obj
            lt_files.append(file_obj)

        try:
            file_obj1 = fileid_obj_map[c[1]]
        except:
            file_obj1 = Files(fileId = c[1] + ":" + token, lastModDate = None, owner = owner, isFile = False)
            fileid_obj_map[c[1]] = file_obj1
            lt_files.append(file_obj1)

        lt_closure.append(Closure(parent_relationship = file_obj, files_relationship = fileid_obj_map[c[1]], owner = owner, depth = c[2]))

    sess.flush()

    for n in idmapper:
        try:
            file_obj = fileid_obj_map[n]
        except:
            #Folder type
            file_obj = Files(fileId = n + token, lastModDate = None, owner = owner, isFile = False)
            fileid_obj_map[n] = file_obj
            lt_files.append(file_obj)

        lt_filenames.append(Filename(fileName = idmapper[n], files = file_obj, owner = owner))

    sess.flush()


    adder(lt_filenames, sess)
    sess.commit()
    adder(lt_closure, sess)

    for i in tdManage:
        logger.debug('joining')
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
        logger.info("donse")
        x.join()


    print("userid: ", userid)

if __name__ == '__main__':
   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()

    wpath = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
    start("testing" + datetime.now().__str__(), wpath)
