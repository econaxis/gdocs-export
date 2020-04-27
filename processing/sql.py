import random
import secrets
from datetime import datetime
from queue import Queue
import pickle
import time
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import logging
import configlog
from processing.models import Owner, Files, Closure, Dates, Base, Filename

scrt = secrets.token_urlsafe(7)
token = datetime.now().strftime("%d-%H.%f") + scrt

PARAMS = os.environ["SQL_CONN"]

ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=15, echo = False, max_overflow=300)
#ENGINE = sqlal.create_engine('sqlite:///foo.db')

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=ENGINE)

CONN = ENGINE.connect()

_session = sessionmaker(bind=ENGINE)

v_scoped_session = scoped_session(_session)

def db_connect(func):
    def inner(*args, **kwargs):
        session = v_scoped_session()
        try:
            func(*args, **kwargs)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
            v_scoped_session.remove()

    return inner


def report(lt_files, print_event):
    while not print_event.is_set():
        logger.info("lt_files size %d ", lt_files.qsize())
        time.sleep(30)

        if random.random() < 0.33:
            p = configlog.sendmail(True)
            time.sleep(10)
            p.join()


def adder(queue, sess):
    counter = 0

    for i in queue:
        counter+=1
        sess.add(i)
        if(counter%60==0):
            logger.info("rem %d/%d", counter, len(queue))
            sess.flush()

    logger.info("flushing adder")
    sess.flush()
    return
    while(not queue.empty()):
        counter +=1
        sess.add(queue.get_nowait())
        if(counter %50 == 0):
            sess.flush()
    sess.flush()


@db_connect
def commit(q, _type = None, add = False):
    sess = v_scoped_session()
    _temp = []
    counter = 0
    iters = round(q.qsize() / 850)
    iters = max(iters, 125)
    logger.info("iters: %d, len: %d", iters, q.qsize())
    while (q.qsize()):
        counter +=1
        try:
            _temp.append(q.get_nowait())
        except:
            break

        if (counter % iters == 0):
            logger.info("flushing, len: %d", q.qsize())
            if(add):
                sess.bulk_save_objects(_temp)
            else:
                sess.bulk_insert_mappings(_type, _temp)

            logger.info("committing")
            sess.commit()
            _temp = []

    logger.debug('while loop done')
    if(_temp and add):
        sess.bulk_save_objects(_temp)
    elif _temp and add:
        sess.bulk_insert_mappings(_type, _temp)

    sess.commit()
    v_scoped_session.remove()
    logger.debug("commit func done")
    return



@db_connect
def load_from_dict(lt_files, fileid_obj_map):
    sess = v_scoped_session()

    secrets.token_urlsafe(3)

    counter = 0
    lt_dates = Queue()

    files = []

    while(lt_files.qsize()):
        file_model, file_data = lt_files.get_nowait()

        files.append((file_model, file_data))
        sess.add(file_model)

        counter +=1
        if(counter % 10 == 0):
            sess.commit()

            for m, d in files:
                fileid = m.id
                bins = d[1][:-1]
                values = d[0]
                bin_width = d[2]

                for counter, _bin_date in enumerate(bins):

                    lt_dates.put(dict(fileId = fileid, bins = bins[counter],  \
                        values = values[counter], bin_width = bin_width))

            files = []

            logger.info(f"len dates: {lt_dates.qsize()}")

            p = [threading.Thread(target = commit, args = (lt_dates, Dates)) for i in range(45)]
            [x.start() for x in p]
            [x.join() for x in p]
            sess.commit()

def start(userid, path):

    sess = v_scoped_session()

    logger.info("STARTING SQL %s %s", userid, path)

    logger.debug("setting sys except hook")

    #Likely a bug? Excepthook not getting called, have to set again

    temp = name=userid[0:15] + datetime.now().strftime("%m %d %h") + scrt
    owner = Owner(name=temp[0:39])

    logger.debug(f"Owner name: {temp[0:39]}")
    sess.add(owner)
    sess.commit()

    global owner_id
    owner_id = owner.id

    sess.close()
    v_scoped_session.remove()

    logger.info("Added owner row, name: %s id: %s", owner.name, owner.id)

    files = {}

    names = pickle.load(open(path+'pickleIndex', 'rb'))


    for n in names[0:1]:
        files.update(pickle.load(open(n, 'rb')))
        continue

        '''
        procs.append(threading.Thread(target = load_from_dict, args = (pickle.load(open(n, 'rb')), owner)))
        procs[-1].start()
        procs[-1].join()
        '''


    lt_files = Queue()
    Queue()
    #fileid_obj_map maps gdrive fileids to file objects defined in models
    fileid_obj_map = {}

    #FILES
    for f in files:
        fileId = f[-1]
        logger.info("File: %s", fileId)
        if(fileId in fileid_obj_map):
            logger.info("duplicated fileid found, skipping")
            continue

        if(files[f]):
            bin_edges = files[f][1]
            #Get last bin edge, convert to datetime
            last_mod = datetime.fromtimestamp(bin_edges[-1])
        else:
            last_mod = None

        file_obj = Files(fileId = fileId + ":"+token + secrets.token_urlsafe(3),
                lastModDate = last_mod, parent_id = owner_id, isFile = True)

        fileid_obj_map[fileId] = file_obj

        lt_files.put((file_obj, files[f]))

    logger.info("len of id map %d len of files %d", len(fileid_obj_map), lt_files.qsize())



    print_event = threading.Event()

    pr = threading.Thread(target = report, args = (lt_files, print_event))
    pr.start()

    p = threading.Thread(target = load_from_dict, args = (lt_files, fileid_obj_map))
    #p1 = threading.Thread(target = load_from_dict, args = (lt_files, fileid_obj_map))
    #p2 = threading.Thread(target = load_from_dict, args = (lt_files, fileid_obj_map))
    #p3 = threading.Thread(target = load_from_dict, args = (lt_files, fileid_obj_map))


    p.start()
    #time.sleep(5)
    #p1.start()
    #time.sleep(5)
    #p2.start()
    #time.sleep(5)
    #p3.start()


    p.join()
    #p1.join()
    #p2.join()
    #p3.join()



    sess = v_scoped_session()

    clos = pickle.load(open(path + 'closure.pickle', 'rb'))
    idmapper = pickle.load(open(path + 'idmapper.pickle', 'rb'))

    logger.debug("Finished loading pickles")


    lt_closure = []
    lt_filenames = []



    add_count = [0, 0]

    for c in clos:
        try:
            file_obj = fileid_obj_map[c[0]]
        except:
            file_obj = Files(fileId = c[0] + ":" + token, lastModDate = None, parent_id = owner_id, isFile = False)
            fileid_obj_map[c[0]] = file_obj
            lt_files.append(file_obj)

        try:
            file_obj1 = fileid_obj_map[c[1]]
        except:
            file_obj1 = Files(fileId = c[1] + ":" + token, lastModDate = None, parent_id = owner_id, isFile = False)
            fileid_obj_map[c[1]] = file_obj1
            lt_files.append(file_obj1)

        lt_closure.append(Closure(parent_relationship = file_obj, files_relationship = fileid_obj_map[c[1]], parent_id = owner_id, depth = c[2]))
        logger.debug("adding lt_closure")
        add_count[0]+=1

    sess.flush()

    for n in idmapper:
        try:
            file_obj = fileid_obj_map[n]
        except:
            #Folder type
            file_obj = Files(fileId = n + token, lastModDate = None, parent_id = owner_id, isFile = False)
            fileid_obj_map[n] = file_obj
            lt_files.put(file_obj)

        lt_filenames.append(Filename(fileName = idmapper[n], files = file_obj, owner_id = owner_id))
        logger.debug("adding lt_filenames")
        add_count[1]+=1

    logger.debug("flushing lt_filenames, lt_closure")

    adder(lt_filenames, sess)

    adder(lt_closure, sess)

    sess.flush()

    logger.warning("Done all filename, closure")


    sess.commit()

    logger.info(f"sql done, added closure: {add_count[0]}, added filename: {add_count[1]}")

    print_event.set()

    pr.join()

    return



if __name__ == '__main__':
   # Owner.__table__.insert(bind = engine).values([dict(name = "default")])
   # sess.add(Owner(name="default"))
   # sess.commit()

    wpath = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
    start("testing" + datetime.now().__str__(), wpath)

