from pprint import PrettyPrinter
from datetime import datetime
from queue import Queue
import time
import threading
import secrets
import sqlalchemy as sqlal
from sqlalchemy.orm import sessionmaker, scoped_session
import os, functools
import logging, configlog

from processing.models import Files, Closure, Dates, Base, Filename

from flaskr.flask_config import Config

logger = logging.getLogger(__name__)

pprint = PrettyPrinter().pprint

scrt = secrets.token_urlsafe(7)
token = datetime.now().strftime("%d-%H.%f") + scrt

PARAMS = os.environ["SQL_CONN"]

sessions = {}
sessions_lock = threading.Lock()


#Global variable for data path
hdatapath = Config.HOMEDATAPATH

logger.warning("hdatapath: %s", hdatapath)

#Used to access files on Azure File Storage, defaults to None to prevent unnecessary connections unless called
az_driver = None

import azure.common

def setup_azure():
    global az_driver
    from azure.storage.file import FileService
    az_driver = FileService(account_name = 'pydocs', account_key = os.environ["AZURESTORAGEKEY"])


def az_download_dbs(owner_id , download_file):
    logger.info("requested az file: %s", owner_id)
    try:
        az_driver.get_file_to_path('def', 'data/dbs', f"{owner_id}.db" , download_file)
    except azure.common.AzureMissingResourceHttpError as e:
        logger.exception("cannot download file")

def az_upload_dbs(owner_id,  from_file):
    upload_path = f"{owner_id}.db"
    try:
        az_driver.create_file_from_path('def', 'data/dbs', upload_path , from_file)
    except azure.common as e:
        logger.exception("canot upload file")

def get_db_path(owner_id):
    return os.path.join(hdatapath, f'dbs/{owner_id}.db')

def reload_engine(owner_id, create_new = False, download = False, lock = None):
    global sessions

    if not lock:
        lock = sessions_lock


    if owner_id in sessions:
        logger.info("found old engine")
        return sessions[owner_id]


    if not az_driver:
        setup_azure()


    with lock:
        #Check if the DB file already exists; if yes, then we load it,
        #else, we download it from AZ file storage

        sqlite_owner_id = get_db_path(owner_id)


        #Only download if the file doesn't exist
        if download and not os.path.isfile(sqlite_owner_id):
            az_download_dbs(owner_id, sqlite_owner_id)
            logger.warning("Downloaded db!")

        if not os.path.isfile(sqlite_owner_id):
            logger.warning(f"SQLITE doesn't exist! {owner_id}")

        #if not create_new and not os.owner_id.isfile(sqlite_owner_id):
            #az_download_dbs(owner_id = owner_id, download_file = sqlite_owner_id)


        logger.warning("RELOADING ENGINE")

        logger.info("Init DB Conn at %s", sqlite_owner_id)

        ENGINE = sqlal.create_engine(f'sqlite:////{sqlite_owner_id}', echo = True,
                                     connect_args=dict(check_same_thread=False))

        Base.metadata.create_all(bind=ENGINE)

        _session = sessionmaker(bind=ENGINE)
        v_scoped_session = scoped_session(_session)


        logger.warning("set session for ownerid %s", owner_id)
        sessions[owner_id] = v_scoped_session

        if download:
            logger.warning("Testing session for any data")
            ds = v_scoped_session().query(Files).all()
            logger.warning("Files Data: %s", ds)


        return v_scoped_session


def db_connect(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):

        #print(kwargs, args)

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


added_list = []


@db_connect
def load_clos(file_data, fileid_obj_map, dict_lock, owner_id=None):
    assert owner_id != None, "Ownerid is none err"
    sess = reload_engine(owner_id)()
    for files in file_data:
        for clos in files.closure:
            with dict_lock:
                if clos.parent[0] not in fileid_obj_map:
                    logger.debug("new element not found: %s", clos.parent[0])

                    fi = Files(fileId=clos.parent[0] + str(owner_id),
                               isFile=False)

                    fi.name = [Filename(files=fi, fileName=clos.parent[1])]
                    sess.add(fi)
                    fileid_obj_map[clos.parent[0]] = fi


                sess.commit()

                if clos.child[0] not in fileid_obj_map:
                    logger.debug("new element not found: %s", clos.child[0])

                    fi = Files(fileId=clos.child[0] + str(owner_id),
                               isFile=False)

                    fi.name = [Filename(files=fi, fileName=clos.child[1])]
                    sess.add(fi)
                    fileid_obj_map[clos.child[0]] = fi

                sess.commit()
                try:
                    sess.add(fileid_obj_map[clos.child[0]])
                    sess.add(fileid_obj_map[clos.parent[0]])

                    child_id = fileid_obj_map[clos.child[0]].id
                    parent_id = fileid_obj_map[clos.parent[0]].id

                    sess.commit()
                    sess.expunge_all()

                    added_list.append((child_id, clos.child[0][-4:]))
                except sqlal.exc.InvalidRequestError as e:
                    logger.exception("clos %s", '+'*30)
                    breakpoint()
                    raise e
                else:
                    cls = Closure(parent=parent_id,
                                  child=child_id,
                                  depth=clos.depth)

                    sess.add(cls)


@db_connect
def load_from_dict(lt_files, dict_lock, owner_id=None):
    assert owner_id != None, "Ownerid is none err"

    sess = reload_engine(owner_id)()

    counter = 0
    Queue()

    while (lt_files.qsize()):

        counter += 1
        file_model, file_data = lt_files.get_nowait()

        sess.add(file_model)

        bulk_dates = []
        for operation in file_data.operations:
            d = Dates(files=file_model,
                      adds=operation.content[0],
                      deletes=operation.content[1],
                      bin_width=None,
                      date=operation.date)
            bulk_dates.append(d)

        logger.debug("bulk saving dates")
        sess.bulk_save_objects(bulk_dates)

        logger.debug("flushing objects")
        logger.debug("new: %s, dirty: %s", sess.new, sess.dirty)
        sess.flush()
        logger.debug("finished flush; file size: %d", lt_files.qsize())

    sess.commit()

    logger.warning("Done load dict")


def start(*args ,**kwargs):
    import sys
    try:
        insert_sql(*args, **kwargs)
    except:
        logger.critical("Exception in SQL!")
        logger.exception("-")
        sys.excepthook(*sys.exc_info())


def insert_sql(userid, files, upload = False):
    logger.debug("Starting sql for userid %s", userid)

    from processing.sql_server import owner_manager


    fileid_obj_map, dict_lock = owner_manager(owner_id=userid)

    sess = reload_engine(userid)()


    logger.info("Checked out owner object, fileid dict, and lock")

    lt_files = Queue()
    #fileid_obj_map maps gdrive fileids to file objects defined in models

    #FILES
    for f in files:
        fileId = f.fileId

        logger.debug("File: %s", fileId)

        if (fileId in fileid_obj_map):
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
            logger.warning("File content empty: %s, %s, operations: %s",
                           f.name, f.fileId, f.operations)
            weighted_avg = None
        else:
            weighted_avg = float(weighted_avg / count_avg)
            weighted_avg = datetime.fromtimestamp(weighted_avg)

        file_obj = Files(fileId=f.fileId + ":" + token +
                         secrets.token_urlsafe(3),
                         lastModDate=weighted_avg,
                         isFile=True)

        file_name = Filename(files=file_obj, fileName=f.name)

        file_obj.name = [file_name]

        with dict_lock:
            fileid_obj_map[fileId] = file_obj

        lt_files.put((file_obj, f))

    SZ_FILES = lt_files.qsize()
    logger.info("len of id map %d len of files %d", len(fileid_obj_map),
                SZ_FILES)

    min(lt_files.qsize(), 5)

    if files:
        p = [
            threading.Thread(target=load_from_dict,
                             args=(lt_files, dict_lock),
                             kwargs=dict(owner_id=userid)) for i in range(1)
        ]
        for x in p:
            x.start()
        for x in p:
            logger.debug("joining threads load_from_dict")
            x.join()

    logger.info("starting load closures")

    load_clos(files, fileid_obj_map,  dict_lock, owner_id = userid)
    sess.commit()
    logger.warning("Done all for owner_id %s; processed files: %d", userid,
                   SZ_FILES)


    if upload:
        db_path = get_db_path(userid)
        az_upload_dbs(owner_id = userid, from_file =db_path)
        logger.warning("Uploaded db at %s", db_path)


    return
    """
    import pickle

    files = pickle.load(open('/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/1.pathed', 'rb'))
    userid = datetime.now().__str__()

    start(userid = userid, files = files)
    """
