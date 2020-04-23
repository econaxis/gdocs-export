import asyncio
import processing.sql
import  multiprocessing as mp
import sys
from time import time
from datetime import datetime
import random
import pickle
from processing.throttler import Throttle
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




# Deprecated


MAX_FILES = 20000
idmapper = {}

acThrottle = None

SEED_ID = "root"

workerInstances = 14

ACCEPTED_TYPES = { "application/vnd.google-apps.presentation", "application/vnd.google-apps.spreadsheet", "application/vnd.google-apps.document", "application/pdf"}

async def getIdsRecursive (drive_url, folders: asyncio.Queue,
                          files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    global MAX_FILES
    # Wait random moment for folder queue to be populated
    await asyncio.sleep(random.uniform(0, 1))

    # Query to pass into Drive to find item

    while (files.qsize() + len(TestUtil.pathedFiles) < MAX_FILES):
        logger.debug("getIdsRecursive looping")
        # Wait for folders queue, with interval 6 seconds between each check
        # Necessary if more than one workers all starting at the same time,
        # with only one seed ID to start

        # Deprecated, do not need to throttle google drive api
        # await drThrottle.sem.acquire()

        await asyncio.sleep(random.uniform(0, 0.5))

        folderIdTuple = await tryGetQueue(folders, name="getIds", interval=3)

        if(folderIdTuple == -1):
            logger.warning('getId task exiting')
            return

        (id, path, retries) = folderIdTuple

        # Root id is different structure
        data = None
        if(id == "root"):
            data = dict(corpora="allDrives", includeItemsFromAllDrives='true',
                        supportsTeamDrives='true')
        else:
            query = "'" + id + "' in parents"
            data = dict(q=query, corpora="allDrives",
                        includeItemsFromAllDrives='true', supportsTeamDrives='true')

        try:
            async with session.get(url=drive_url, params=data, headers=headers) as response:
                resp = await TestUtil.handleResponse(response,  folderIdTuple, queue = folders)
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

        global idmapper
        for resFile in resp["files"]:
            ent_name = "".join(["" if c in ['\"', '\'', '\\']
                        else c for c in resFile["name"]]).rstrip()[0:298]
            id = resFile["id"]
            idmapper[id] = ent_name
            if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put((id, path + [id], 0))
            elif (resFile["mimeType"] in ACCEPTED_TYPES):
                # First element id is not used for naming, only for api calls
                await files.put([id, resFile["mimeType"], path + [id], 0])


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
                acThrottle.increase()
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
        if((*path,) not in TestUtil.pathedFiles):
            TestUtil.pathedFiles[(*path,)] = [modifiedDate]
        else:
            TestUtil.pathedFiles[(*path,)].append(modifiedDate)
    return 0

async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers, endEvent):

    # Await random amount for more staggered requesting (?)
    await asyncio.sleep(random.uniform(0, 6))
    while not endEvent.is_set():
        logger.debug("getRevision looping")
        await acThrottle.acquire()

        fileTuple = await tryGetQueue(files, name="getRevision")
        if(fileTuple == -1):
            logger.warning('getRevision task exiting')
            break

        (fileId, mimeType, path, tried) = fileTuple

        if(len(TestUtil.pathedFiles) > 10):
            #Sleep to avoid xs memory usage
            await asyncio.sleep(10)


        if(mimeType != "application/vnd.google-apps.document"):
            logger.debug("not google doc")
            await queryDriveActivity(fileTuple, files, session, headers)
        else:
            gd = GDoc()

            dates = await gd.async_init(fileId, session, headers)
            TestUtil.pathedFiles[(*path,)] = dates
            logger.debug("google doc")
            #TestUtil.pathedFiles[(*path,)] = []
            #dates = TestUtil.pathedFiles[(*path,)]
            #getgdoc(TestUtil.creds, fileId, dates)

    secs = 30
    logger.warning("getRevision task has ended, waiting for {x} seconds for all other tasks to finish", x = secs)
    await asyncio.sleep(secs)
    endEvent.set()
    logger.warning("Close event has been set. Expect print task to finish soon")


async def start():
    global acThrottle

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)

    acThrottle = Throttle(30)
    TestUtil.throttle = acThrottle

    folders = asyncio.Queue()
    files = asyncio.Queue()
    await folders.put([SEED_ID, ["root"], 0])

    tt = asyncio.create_task(acThrottle.work())

    async with aiohttp.ClientSession() as session:
        # Generate list of Workers to explore folder structure

        endEvent = asyncio.Event()

        fileExplorers = [loop.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files",
                                                             folders, files, session, TestUtil.headers)) for i in range(workerInstances)]

        revisionExplorer = [loop.create_task(getRevision(files, session, TestUtil.headers, endEvent))
                            for i in range(10)]

        # Generate Print Task that prints data every X seconds
        printTask = loop.create_task( TestUtil.print_size(files, endEvent))
        # Wait until all folders are properly processed, or until FILE_MAX is
        # reached

        await asyncio.gather(*revisionExplorer, *fileExplorers, printTask)
        logger.info("await gather revisions done")



    tt.cancel()
    printTask.cancel()

    logger.warning("cancelled throttler")

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



    if(fileId is not None):
        global SEED_ID
        global idmapper
        SEED_ID = fileId
        idmapper[SEED_ID] = 'root'

    # Main loop
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    startTask = loop.create_task(start())

    loop.run_until_complete(asyncio.gather(startTask))

    logger.warning("loop done")

    if(len(TestUtil.pathedFiles) == 0):
        return "No files found for this id. check invalid"

    d = set()
    for l1 in TestUtil.pathedFiles:
        for i1, path in enumerate(l1):
            path2 = l1[-1]
            d.update([(path, path2, len(l1) - i1 - 1)])


    pickle.dump(d, open(_workingPath + 'closure.pickle', 'wb'))
    pickle.dump(TestUtil.pathedFiles, open(_workingPath + 'pathedFiles.pickle', 'wb'))
    pickle.dump(idmapper, open(_workingPath + 'idmapper.pickle', 'wb'))
    pickle.dump(TestUtil.pickleIndex, open(_workingPath + 'pickleIndex', 'wb'))




    # Writing data to SQL
    processing.sql.start(USER_ID, _workingPath)

    open(_workingPath + 'done.txt', 'a+').write("DONE")
    raise AssertionError("Program ended normally. This assertion is to send SMTP logs by syshook handler")


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
'''
