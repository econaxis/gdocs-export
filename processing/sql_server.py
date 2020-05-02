import asyncio
import os
import time
from processing.datutils.test_utils import adv_read, adv_write
import processing.sql as sql
import pickle
import configlog
import threading
import logging

logger = logging.getLogger(__name__)

#Needs high memory to run, the higher threads
QUEUE_SIZE = 30
THREAD_SIZE = 100

from processing.sql_owner import OwnerManager

owner_manager = OwnerManager()

finished_threads = 0



def report(queue, threads, print_event):
    counter = 0
    while not print_event.is_set():
        logger.info("SQL Queue size: %d, thread size: %d", queue.qsize(), len(threads))
        remove_dead_threads(threads)
        time.sleep(10)
        counter += 1
        if counter % 10 == 0:
            configlog.sendmail(msg = "From SQL")


def exchandler(loop, context):
    logger.critical(context)
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")


#Used for debugging
async def send_socket():

    info_packet = pickle.load(open('info_packet', 'rb'))

    info_packet = info_packet._replace(userid="send_socket" + str(time.time()))

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

    logger.debug("handle_request")


    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    loop.set_debug(True)


    async def req_callback(reader, writer):
        nonlocal queue

        logger.debug('request received')

        starting_message = await adv_read(reader)

        #Starting messages other than request are denied
        assert starting_message == b'request'

        message = b""

        logger.info("queue size: %d"%queue.qsize())
        if(queue.qsize() > QUEUE_SIZE):
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
                logger.debug("Put new task in queue")
            else:
                logger.debug("Received extra info: %s", info.extra)


    server = await asyncio.start_server(
        req_callback, '0.0.0.0', 8888)

    #Used for debugging

    if "FLASKDBG" in os.environ:
        reps = 10
        while reps:
            reps-=1
            asyncio.create_task(send_socket())

    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

def start_server(queue):
    asyncio.run(handle_request(queue))


def remove_dead_threads(threads):
    global finished_threads

    removed_count = 0
    for i in threads:
        if not i.is_alive():
            i.join(timeout=2)
            threads.remove(i)
            removed_count += 1
            finished_threads += 1
            logger.debug("removed thread, done")
    logger.info("Removed finished threads: %d, total resolved threads: %d", removed_count, finished_threads)
    return


def queue_worker(queue, threads):
    while True:
        print("new task")

        latest = queue.get()

        while len(threads) > THREAD_SIZE:
            logger.debug("threads too many, sleeping")
            time.sleep(20)

            logger.info("done waiting join, resulting thread size %d", len(threads))

        ts = threading.Thread(target = sql.start, kwargs = dict(userid = latest.userid, files = latest.files))
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

    exec_tasks = []

    executor = concurrent.futures.ThreadPoolExecutor(max_workers = 2)

    exec_tasks.append(executor.submit(start_server, queue))
    exec_tasks.append(executor.submit(queue_worker, queue, threads))

    ds = concurrent.futures.wait(exec_tasks, return_when = concurrent.futures.FIRST_EXCEPTION)

    logger.critical("Tasks ended")

    print_event.set()

    logger.warning("concurrent futures done. The program has exited")

    for res in ds.done:
        if(res.exception()):
            exc =  res.exception()

            executor._threads.clear()
            concurrent.futures.thread._threads_queues.clear()

            raise exc

    pr.join()


if __name__ == '__main__':
    logger.warning("STARTING SQL SERVER")
    thread_pool()

