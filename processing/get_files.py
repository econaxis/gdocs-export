import asyncio
import  multiprocessing as mp
from multiprocessing import Process, Pipe
from pprint import pformat
from time import time
from datetime import datetime
import random
import pickle
import aiohttp
import pprint
import iso8601
from pathlib import Path
import logging
import configlog

# Imports TestUtil and corresponding functions
from processing.datutils.test_utils import *
from processing.gdoc import GDoc

logger = logging.getLogger(__name__)

pprint = pprint.PrettyPrinter(indent=4).pprint

timeout = aiohttp.ClientTimeout(total=8)

MAX_FILES = 150

SEED_ID = "root"

workerInstances = 3

ACCEPTED_TYPES = {"application/vnd.google-apps.document"}

from collections import namedtuple

temp_file = namedtuple('temp_file', ['id', 'name', 'type', 'path'])


#For managing duplicates
tot_folders = {}




async def getIdsRecursive (drive_url, folders: asyncio.Queue,
                          files: asyncio.Queue, session: aiohttp.ClientSession, headers, done_event):


    # Query to pass into Drive to find item

    while (TestUtil.processedcount + files.qsize() + len(TestUtil.files) < MAX_FILES) and not done_event.is_set():
        # Wait for folders queue, with interval 6 seconds between each check
        # Necessary if more than one workers all starting at the same time,
        # with only one seed ID to start

        # Deprecated, do not need to throttle google drive api
        # await drThrottle.sem.acquire()

        proc_file = await tryGetQueue(folders, name="getIds", interval=3,repeatTimes = 20)


        if(proc_file == -1):
            break

        # Root id is different structure
        if(proc_file.id == "root"):
            data = dict(corpora="allDrives", includeItemsFromAllDrives='true',
                        supportsTeamDrives='true',
                        fields = 'files/mimeType, files/id, files/name, files/capabilities/canReadRevisions')
        else:
            query = "'" + proc_file.id + "' in parents"
            data = dict(q=query, corpora="allDrives",
                        includeItemsFromAllDrives='true', supportsTeamDrives='true',
                        fields = 'files/mimeType, files/id, files/name, files/capabilities/canReadRevisions')

        try:
            async with session.get(url=drive_url, params=data, headers=headers) as response:
                resp = await TestUtil.handleResponse(response)
                if(resp == -1):
                    del resp
                    del response
                    continue
        #except aiohttp.client_exceptions:
        except:
            secs = random.uniform(5, 40)
            logger.exception("connection closed prematurely with gdrive, sleeping for %d", secs)
            await asyncio.sleep(secs)
            continue

        # Parse file and folder names to make them filesystem safe, limit to
        # 120 characters


        for resFile in resp["files"]:
            id = resFile["id"]


            ent_name = "".join(["" if c in ['\"', '\'', '\\', '"', "'"]
                        else c for c in resFile["name"]]).rstrip()[0:298]

            f = temp_file(name = ent_name, id = id, path = proc_file.path + [(id, ent_name)], type = resFile["mimeType"])

            if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put((f))
            elif (resFile["mimeType"] in ACCEPTED_TYPES):
                # First element id is not used for naming, only for api calls
                if not resFile["capabilities"]["canReadRevisions"] or id in tot_folders:
                     continue
                tot_folders[id] = True
                await files.put(f)



    logger.info("----------------------------------getid return")
    logger.info("len %d:%d:%d", TestUtil.processedcount, files.qsize(), len(TestUtil.files))



async def getRevision(files, session: aiohttp.ClientSession, headers, endEvent, name = 'default'):

    # Await random amount for more staggered requesting (?)
    await asyncio.sleep(random.uniform(0, workerInstances * 1))

    _t = time.time()

    cycles = 0

    while not endEvent.is_set():
        #await asyncio.sleep(random.uniform(0, 1))
        cycles +=1

        proc_file = await tryGetQueue(files, name="getRevision")

        if(proc_file == -1):
            logger.warning('getRevision task exiting')
            break

        gd = GDoc()
        await gd.async_init(proc_file.name, proc_file.id, session, TestUtil.headers, proc_file.path)

        gd.compute_closure()


        if gd.done and gd.operations:
            TestUtil.files.append(gd)
        else:
            logger.warning("not done but tried to append, prob because no operations found file: %s, %s", gd.fileId, gd.name)


    endEvent.set()
    logger.info("getrev return")

    return

    if(not endEvent.is_set()):
        secs = 10
        logger.warning(f"getRevision task has ended, waiting for {secs} seconds for all other tasks to finish")
        await asyncio.sleep(secs)
        endEvent.set()
        logger.warning("Close event has been set. Expect print task to finish soon")

    logger.info("getrev return")

async def start():

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    loop.set_debug(True)


    print("TESTING SOCKET SEND")

    start_succ = False

    while not start_succ:
        try:
            ex = Info (extra = "testing extra function from start()")
            await TestUtil.send_socket(ex)
        except:
            logger.exception("Starting socket send failed, retrying after 5s")
            await asyncio.sleep(5)
        else:
            start_succ = True



    print("==== END ====")


    folders = asyncio.Queue()
    files = asyncio.Queue()

    first_folder = temp_file(name = 'root', id = 'root', type = '', path = [('root', 'root')])

    await folders.put(first_folder)


    async with aiohttp.ClientSession(timeout = timeout) as session:
        # Generate list of Workers to explore folder structure

        endEvent = asyncio.Event()

        fileExplorers = [loop.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files", \
                                         folders, files, session, TestUtil.headers, endEvent)) for i in range(1)]

        revisionExplorer = [loop.create_task(getRevision(files, session, TestUtil.headers, endEvent))
                            for i in range(workerInstances)]

        # Generate Print Task that prints data every X seconds
        printTask = loop.create_task( TestUtil.print_size(files, endEvent))
        # Wait until all folders are properly processed, or until FILE_MAX is
        # reached

        await asyncio.gather(*revisionExplorer, *fileExplorers, printTask)

        logger.info("await gather revisions done")

    await TestUtil.dump_files()

    printTask.cancel()

    logger.info("start() task done")


def exchandler(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")
    asyncio.create_task(shutdown(loop))


async def shutdown(loop, signal=None):
    """Cleanup tasks tied to the service's shutdown."""

    from configlog import sendmail
    if signal:
        logging.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    logging.info("Emailing logs...")
    sendmail()
    logging.info("Stopping")
    loop.stop()

def loadFiles(USER_ID, _workingPath, fileId, _creds):

    logger.info("Start loadFiles, %s %s", USER_ID, fileId)

    Path(_workingPath).mkdir(exist_ok=True)



    # Load pickle file. Should have been made by Flask/App.py
    # in authorization step

    TestUtil.refresh_creds(_creds)
    TestUtil.workingPath = _workingPath
    TestUtil.userid = USER_ID



    if(fileId is not None):
        global SEED_ID
        SEED_ID = fileId
        TestUtil.idmapper[SEED_ID] = 'root'

    # Main loop
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    startTask = loop.create_task(start())

    loop.set_debug(True)

    loop.run_until_complete(asyncio.gather(startTask))

    logger.warning("loop done")

    #Dump files before proceeding
    #TestUtil.dump_files()


    #pickle.dump(TestUtil.closure, open(_workingPath + 'closure.pickle', 'wb'))
    #pickle.dump(TestUtil.pathedFiles, open(_workingPath + 'pathedFiles.pickle', 'wb'))
    #pickle.dump(TestUtil.idmapper, open(_workingPath + 'idmapper.pickle', 'wb'))
    #pickle.dump(TestUtil.pickleIndex, open(_workingPath + 'pickleIndex', 'wb'))

    logger.info("dumped pickle files")




    # Writing data to SQL
    #import processing.sql
    #processing.sql.start(USER_ID, _workingPath)

    #open(_workingPath + 'done.txt', 'a+').write("DONE")
    configlog.sendmail(msg = "program ended successfully")
    logger.info("Program ended successfully for userid %s", USER_ID)


'''
 #   asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy
if __name__ == "__main__":
    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"
    homePath = "/home/henry/pydocs/"

    fileid = "0B4Fujvv5Mfqba28zX3gzWlBoTzg"

    import os
    if("DBGHPATH" in os.environ):
        homePath = os.environ["DBGHPATH"]

    workingPath = homePath + 'data/' + uid + '/'
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    CREDENTIAL_FILE = 'service.json'
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, workingPath, fileid, creds)
async def queryDriveActivity(fileTuple, files, session, headers):

    (fileId, mimeType, path, tried) = fileTuple

    try:
        async with session.get(url=dr2_urlbuilder(fileId), headers=headers) as revResponse:
            code = await TestUtil.handleResponse(revResponse, fileTuple,queue = files)
            if code == -1:
                _revisions = dict()
            else:
                _revisions = code
            del code

        async with session.post(**TestUtil.dractivity_builder(fileId)) as actResponse:
            code = await TestUtil.handleResponse(actResponse,  fileTuple, queue = files)
            if code == -1:
                return -1
            else:
                activities = code
            del code
    #except aiohttp.client_exceptions:
    except:
        logger.exception('EXCEPTION', exc_info = True)
        secs = random.uniform(5, 30)
        logger.warning('Because of exception, sleeping for %d', secs)
        await asyncio.sleep(secs)
        return -1


    # No items will be found if the first drive revision returns an error
    # This occurs when the user doesn't have permission
    _revisions = _revisions.get('items', [])

    activities = activities.get("activities", [])

    for a in activities:
        _revisions.append(dict(modifiedDate=a["timestamp"]))


    for item in _revisions:
        modifiedDate = iso8601.parse_date(item["modifiedDate"])

        timestamp = datetime.timestamp(modifiedDate)

        #TODO: don't use TestUtil.pathedFiles, use pipe instead for multiprocessing lib use
        if((*path,) not in TestUtil.pathedFiles):
            TestUtil.pathedFiles[(*path,)] = [timestamp]
        else:
            TestUtil.pathedFiles[(*path,)].append(timestamp)
    return 0

'''
