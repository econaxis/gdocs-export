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
from processing.models import  Files, Closure, Dates, Base, Filename


logger = logging.getLogger(__name__)


pprint = PrettyPrinter().pprint

scrt = secrets.token_urlsafe(7)
token = datetime.now().strftime("%d-%H.%f") + scrt

PARAMS = os.environ["SQL_CONN"]



sessions = {}
sessions_lock = threading.Lock()

def reload_engine(path):
    global sessions, sessions_lock

    with sessions_lock:
        if path in sessions:
            return sessions[path]

        print("creating new database for ", path)
        ENGINE = sqlal.create_engine(f'sqlite:///data/dbs/{path}.db', connect_args = dict(check_same_thread=False))

        Base.metadata.create_all(bind=ENGINE)
        _session = sessionmaker(bind=ENGINE)
        v_scoped_session = scoped_session(_session)


        sessions[path] = v_scoped_session
        return v_scoped_session

def db_connect(func):

    @functools.wraps(func)
    def inner(*args, **kwargs):

        print(kwargs, args)

        print("userid: ", kwargs["owner_id"])
        session_manager = reload_engine(kwargs["owner_id"])
        session = session_manager()
        try:
            result = func(*args, **kwargs)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
            session_manager.remove()
        return result
    return inner

@db_connect
def load_clos(file_data, fileid_obj_map, dict_lock, owner_id = None):
    assert owner_id != None, "Ownerid is none err"
    sess = reload_engine(owner_id)()
    for files in file_data:
        for clos in files.closure:
            time.sleep(1)
            with dict_lock:
                if "{}.id".format(clos.parent[0]) not in fileid_obj_map:
                    logger.debug("new element not found: %s", clos.parent[0])

                    fi = Files(fileId = clos.parent[0] + str(owner_id), 
                            isFile = False)

                    file_name = Filename (files = fi, fileName = clos.parent[1])
                    fi.name = [file_name]

                    try:
                        sess.add(fi)
                        sess.flush()
                    except:
                        logger.exception("sqlexc: ")
                        sess.rollback()
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
                    cls = Closure(parent = parent_id, child = child_id, depth = clos.depth)
                    sess.add(cls)

@db_connect
def load_from_dict(lt_files, dict_lock, owner_id = None):
    assert owner_id != None, "Ownerid is none err"


    sess = reload_engine(owner_id)()

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

    sess.commit()

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

    sess = reload_engine(userid)()

    fileid_obj_map, dict_lock = owner_manager(owner_id = userid)

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
                lastModDate = weighted_avg, isFile = True)

        file_name = Filename(files = file_obj,  fileName = f.name)

        file_obj.name = [file_name]

        with dict_lock:
            fileid_obj_map[fileId] = file_obj

        lt_files.put((file_obj, f))


    SZ_FILES = lt_files.qsize()
    logger.info("len of id map %d len of files %d", len(fileid_obj_map), SZ_FILES)

    t_size = min(lt_files.qsize(), 5)


    if files:
        p = [threading.Thread(target = load_from_dict, args = (lt_files, dict_lock), kwargs = dict(owner_id = userid)) for i in range(1)]
        for x in p:
            x.start()
        for x in p:
            logger.debug("joining threads load_from_dict")
            x.join()

    logger.info("starting load closures")

    #load_clos(files, fileid_obj_map,  dict_lock, owner_id = owner_id)
    sess.commit()
    logger.warning("Done all for owner_id %s; processed files: %d",userid,  SZ_FILES)
    return



    """
    import pickle

    files = pickle.load(open('/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/1.pathed', 'rb'))
    userid = datetime.now().__str__()

    start(userid = userid, files = files)
    """
