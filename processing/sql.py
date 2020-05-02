import random
import functools
from pprint import PrettyPrinter
import secrets
from datetime import datetime
from queue import Queue
import time
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import logging
import configlog
from processing.models import Owner, Files, Closure, Dates, Base, Filename


pprint = PrettyPrinter().pprint

scrt = secrets.token_urlsafe(7)
token = datetime.now().strftime("%d-%H.%f") + scrt

PARAMS = os.environ["SQL_CONN"]



if "FLASKDBG" in os.environ or True:
    ENGINE = sqlal.create_engine('sqlite:///ds.db', connect_args = dict(check_same_thread=False))
else:
    ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=30, echo = True, max_overflow=300)


logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=ENGINE)

_session = sessionmaker(bind=ENGINE)

v_scoped_session = scoped_session(_session)

def db_connect(func):

    @functools.wraps(func)
    def inner(*args, **kwargs):
        session = v_scoped_session()
        try:
            result = func(*args, **kwargs)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
            v_scoped_session.remove()
        return result
    return inner


"""
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
"""


@db_connect
def load_clos(file_data, fileid_obj_map, owner_id, dict_lock):
    sess = v_scoped_session()
    for files in file_data:
        for clos in files.closure:
            time.sleep(1)
            with dict_lock:
                if "{}.id".format(clos.parent[0]) not in fileid_obj_map:
                    logger.debug("new element not found: %s", clos.parent[0])

                    fi = Files(fileId = clos.parent[0] + str(owner_id), parent_id = owner_id,
                            isFile = False)

                    file_name = Filename (files = fi, owner_id = owner_id, fileName = clos.parent[1])
                    fi.name = [file_name]

                    try:
                        sess.add(fi)
                        sess.flush()
                    except:
                        logger.exception("sqlexc: ")
                    else:
                        fileid_obj_map[clos.parent[0]] = fi
                        fileid_obj_map[clos.parent[0]+'.id'] = fi.id
                        sess.commit()
                try:
                    sess.add(fileid_obj_map[clos.child[0]])
                    child_id = fileid_obj_map[clos.child[0]].id
                    #sess.add(fileid_obj_map[clos.parent[0]])
                    parent_id = fileid_obj_map[clos.parent[0]+'.id']
                except:
                    logger.exception("clos")
                else:
                    cls = Closure(parent = parent_id, child = child_id, owner_id = owner_id, depth = clos.depth)
                    sess.add(cls)

@db_connect
def load_from_dict(lt_files, owner_id, dict_lock):
    sess = v_scoped_session()

    counter = 0
    lt_dates = Queue()

    files = []

    while(lt_files.qsize()):

        counter += 1
        file_model, file_data = lt_files.get_nowait()

        sess.add(file_model)

        bulk_dates = []
        for operation in file_data.operations:
            d = Dates(files = file_model, adds = operation.content[0],
                    deletes = operation.content[1], bin_width = None, date = operation.date)
            bulk_dates.append(d)

        logger.debug("bulk saving dates")
        sess.bulk_save_objects(bulk_dates)

        logger.debug("flushing objects")
        logger.debug("new: %s, dirty: %s", sess.new, sess.dirty)
        sess.flush()
        logger.debug("finished flush; file size: %d", lt_files.qsize())


    sess.expunge_all()
    sess.commit()
    v_scoped_session.remove()

    logger.warning("Done load dict")



def start(userid, files):
    import sys
    try:
        insert_sql(userid, files)
    except:
        logger.critical("Exception in SQL!")
        logger.exception("-")
        sys.excepthook(*sys.exc_info())


def insert_sql(userid, files):
    logger.debug("Starting sql for userid %s", userid)

    from processing.sql_server import owner_manager

    sess = v_scoped_session()

    owner_id, fileid_obj_map, dict_lock = owner_manager(userid)

    logger.info("Checked out owner object, fileid dict, and lock")


    lt_files = Queue()
    #fileid_obj_map maps gdrive fileids to file objects defined in models


    #FILES
    for f in files:
        fileId = f.fileId

        logger.debug("File: %s", fileId)

        if(fileId in fileid_obj_map):
            #Duplicate id found?
            logger.warning("Duplicated file id found: %s", fileId)
            continue

        weighted_avg = 0
        count_avg = 0

        for o in f.operations:
            weighted_avg += o.date * (o.content[0] + o.content[1])
            count_avg += o.content[0] + o.content[1]

        if not count_avg or not weighted_avg:
            #Go to next file, this file has no data, and avoid division by zero error
            logger.warning("File content empty: %s, %s, operations: %s", f.name, f.fileId, f.operations)
            weighted_avg = None
        else:
            weighted_avg = float(weighted_avg / count_avg)
            weighted_avg = datetime.fromtimestamp(weighted_avg)


        file_obj = Files(fileId = f.fileId + ":"+token + secrets.token_urlsafe(3),
                lastModDate = weighted_avg, parent_id = owner_id,
                isFile = True)

        file_name = Filename(files = file_obj, owner_id = owner_id, fileName = f.name)

        file_obj.name = [file_name]

        with dict_lock:
            fileid_obj_map[fileId] = file_obj

        lt_files.put((file_obj, f))


    SZ_FILES = lt_files.qsize()
    logger.info("len of id map %d len of files %d", len(fileid_obj_map), SZ_FILES)

    t_size = min(lt_files.qsize(), 5)


    if files:
        p = [threading.Thread(target = load_from_dict, args = (lt_files, owner_id, dict_lock)) for i in range(1)]
        for x in p:
            x.start()
        for x in p:
            logger.debug("joining threads load_from_dict")
            x.join()

    logger.info("starting load closures")

    load_clos(files, fileid_obj_map, owner_id, dict_lock)
    sess.commit()
    logger.warning("Done all for owner_id %s; processed files: %d", owner_id, SZ_FILES)
    return



    """
    import pickle

    files = pickle.load(open('/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/1.pathed', 'rb'))
    userid = datetime.now().__str__()

    start(userid = userid, files = files)
    """
