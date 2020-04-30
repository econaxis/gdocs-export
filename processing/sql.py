import random
from processing.datutils.test_utils import adv_read, adv_write
import functools
import sys
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

ENGINE = sqlal.create_engine("mssql+pyodbc:///?odbc_connect=%s" % PARAMS, pool_size=30, echo = False, max_overflow=300)
#ENGINE = sqlal.create_engine('sqlite:///foo1.db')

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=ENGINE)

CONN = ENGINE.connect()

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


def report(queue, threads, print_event):
    counter = 0
    while not print_event.is_set():
        logger.info("SQL Queue size: %d, thread size: %d", queue.qsize(), len(threads))
        time.sleep(5)
        counter += 1
        if counter % 20 == 0:
            configlog.sendmail(msg = "From SQL")



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

    if(add):
        sess.bulk_save_objects(_temp)
    else:
        sess.bulk_insert_mappings(_type, _temp)


    sess.commit()
    v_scoped_session.remove()
    logger.info("commit func done")
    return


@db_connect
def load_clos(file_data, fileid_obj_map, owner_id, dict_lock):
    sess = v_scoped_session()
    for files in file_data:
        for clos in files.closure:
            with dict_lock:
                if clos.parent[0] not in fileid_obj_map:
                    logger.info("new element not found: %s", clos.parent[0])

                    fi = Files(fileId = clos.parent[0] + str(owner_id), parent_id = owner_id,
                            isFile = False)

                    file_name = Filename (files = fi, owner_id = owner_id, fileName = clos.parent[1])
                    fi.name = [file_name]

                    sess.add(fi)
                    fileid_obj_map[clos.parent[0]] = fi

                file_model = fileid_obj_map[clos.parent[0]]

                cls = Closure(parent_relationship = fileid_obj_map[clos.parent[0]],
                        files_relationship = file_model, depth = clos.depth,
                        owner_id = owner_id)

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

        for operation in file_data.operations:
            d = Dates(files = file_model, adds = operation.content[0],
                    deletes = operation.content[1], bin_width = None, date = operation.date)
            sess.add(d)


        logger.info("flushing objects")
        logger.debug("new: %s, dirty: %s", sess.new, sess.dirty)
        sess.flush()
        logger.info("finished flush; file size: %d", lt_files.qsize())

    sess.commit()
    v_scoped_session.remove()


import asyncio

import collections

path = '/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/1.pathed'
#data = pickle.load(open(path, 'rb'))


def exchandler(loop, context):
    print(context)
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")


async def send_socket():
    info_packet = pickle.load(open('info_packet', 'rb'))

    logger.info("connect working")
    r, w = await asyncio.open_connection('127.0.0.1', 8888)

    message= b"request"


    await adv_write(w, message)

    m = await adv_read(r)
    logger.info("received: %s", m)

    while m != b'go':
        return False


    if m == b'go':
        await adv_write(w, info_packet, to_pickle = True)

    w.close()
    return True



async def handle_request(queue):

    print("handle_request")


    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    loop.set_debug(True)


    async def req_callback(reader, writer):
        nonlocal queue

        from pprint import pformat
        print('request received')



        starting_message = await adv_read(reader)

        print(starting_message)
        assert starting_message == b'request'

        message = ""
        print("queue size: %d"%queue.qsize())
        if(queue.qsize() > 3):
            message = b"wait"
            logger.warning("Job denied because queue was too large")
            job_received = False
        else:
            message = b"go"
            job_received = True

        await adv_write(writer, message)

        if job_received:

            info = await adv_read(reader)
            print("name: ", info.userid)

            if info.extra == None:
                queue.put(info)
                print("put in queue")
            else:
                print(info.extra)


    server = await asyncio.start_server(
        req_callback, '0.0.0.0', 8888)


    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

def start_server(queue):
    asyncio.run(handle_request(queue))



def queue_worker(queue, threads):
    while True:
        print("new task")
        latest = queue.get()
        files = latest

        while len(threads) > 5:
            print("threads too many, sleeping")
            threads[0].join()
            threads.pop(0)

            for i in threads:
                if not i.is_alive():
                    i.join(timeout=0.01)
                    threads.remove(i)

            print("done waiting join")

        ts = threading.Thread(target = start, kwargs = dict(userid = latest.userid, files = latest.files))
        ts.start()
        threads.append(ts)



def thread_pool():

    import concurrent.futures
    from queue import Queue
    
    print_event = threading.Event()


    queue = Queue()
    threads = []

    pr = threading.Thread(target = report, args = (queue, threads, print_event))
    pr.start()

    f = []

    executor = concurrent.futures.ThreadPoolExecutor(max_workers = 2)

    f.append(executor.submit(start_server, queue))
    f.append(executor.submit(queue_worker, queue, threads))

    ds = concurrent.futures.wait(f, return_when = concurrent.futures.FIRST_EXCEPTION)

    print_event.set()

    print("rand")
    for res in ds.done:
        print("starting")

        if(res.exception()):
            exc =  res.exception()

            executor._threads.clear()
            concurrent.futures.thread._threads_queues.clear()

            raise exc




def start(userid, files):

    from processing.sql_owner import OwnerManager
    get_owner = OwnerManager()


    sess = v_scoped_session()



    owner, fileid_obj_map, dict_lock = get_owner(userid)
    sess.add(owner)
    owner_id = owner.id

    print("owner id: ", owner_id)


    lt_files = Queue()
    #fileid_obj_map maps gdrive fileids to file objects defined in models


    #FILES
    for f in files:
        fileId = f.fileId

        logger.info("File: %s", fileId)

        if(fileId in fileid_obj_map):
            pass
        #    logger.info("duplicated fileid found, skipping")
            #continue

        #Check if both lists (values and bins) are filled
        if(f.operations):
            weighted_avg = 0
            count_avg = 0

            for o in f.operations:
                if not (o.content[0] or o.content[1]):
                    continue
                weighted_avg += o.date * (o.content[0] + o.content[1])
                count_avg += o.content[0] + o.content[1]

            weighted_avg = float(weighted_avg / count_avg)
            weighted_avg = datetime.fromtimestamp(weighted_avg)
        else:
            continue

        file_obj = Files(fileId = f.fileId + ":"+token + secrets.token_urlsafe(3),
                lastModDate = weighted_avg, parent_id = owner_id,
                isFile = True)

        file_name = Filename(files = file_obj, owner_id = owner_id, fileName = f.name)
        file_obj.name = [file_name]
        with dict_lock:
            fileid_obj_map[fileId] = file_obj

        lt_files.put((file_obj, f))

    logger.info("len of id map %d len of files %d", len(fileid_obj_map), lt_files.qsize())

    t_size = min(lt_files.qsize(), 4)


    if files:
        p = [threading.Thread(target = load_from_dict, args = (lt_files, owner_id, dict_lock)) for i in range(5)]
        for x in p:
            x.start()
        for x in p:
            logger.info("joining")
            x.join()

    logger.info("starting load closures")

    load_clos(files, fileid_obj_map, owner_id, dict_lock)


    sess.commit()

    logger.warning("Done all filename, closure")
    return



if __name__ == '__main__':

    thread_pool()

    """

    files = pickle.load(open('/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/1.pathed', 'rb'))
    userid = datetime.now().__str__()

    start(userid = userid, files = files)
    """
