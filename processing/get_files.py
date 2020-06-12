# download (thread pool) 0.512
# executor submit 3.017
# gdoc 3.126419

import asyncio
from collections import namedtuple
import random
import aiohttp
import pprint
from pathlib import Path
import logging
import os
import configlog

# Imports TestUtil and corresponding functions
from processing.datutils.test_utils import TestUtil,  tryGetQueue
from processing.gdoc import GDoc
from processing import gdoc
pprint = pprint.PrettyPrinter(indent=4).pprint

logger = logging.getLogger(__name__)



timeout = aiohttp.ClientTimeout(total=15)

SEED_ID = "root"

workerInstances = 4

ACCEPTED_TYPES = "application/vnd.google-apps.document"

temp_file = namedtuple('temp_file', ['id', 'name', 'type', 'path', 'last_revision_id'])

#For managing duplicates
tot_files = {}

collection_done = asyncio.Event()

async def getIdsWrapper(*args, **kwargs):
    try:
        await getIdsRecursive(*args, **kwargs)
    except Exception as e:
        logger.exception("Exception!")
        shutdown(asyncio.get_event_loop())


async def getIdsRecursive(drive_url, folders: asyncio.Queue,
                          files: asyncio.Queue, session: aiohttp.ClientSession,
                          headers, endEvent):

    # This is the common data-dict to be passed into all our HTTP requests.
    # We need to fill out the q variable, depending on the folder id being requested
    data = dict(
        q="",
        corpora="allDrives",
        includeItemsFromAllDrives='true',
        supportsTeamDrives='true',
        fields='files/mimeType, files/id, files/name, files/capabilities/canReadRevisions',
        pageSize=1000)
    # Query to pass into Drive to find item

    while not endEvent.is_set():
        # Wait for folders queue, with interval 6 seconds between each check
        # Necessary if more than one workers all starting at the same time,
        # with only one seed ID to start

        def stop(method = None):
            if TestUtil.calc_totsize() - 10> TestUtil.MAX_FILES and not endEvent.is_set():
                # Return the diff
                if method == "diff":
                    return TestUtil.totsize - TestUtil.MAX_FILES
                else:
                    return True
            else:
                return 0

        if (stop()):
            sleep_time = stop("diff") / 2
            logger.info("getIds sleeping %f", sleep_time)
            await asyncio.sleep(sleep_time)

        proc_file = await tryGetQueue(folders,
                                      name="getIds",
                                      interval=5,
                                      repeatTimes=8,
                                      endEvent = endEvent)

        if (proc_file == -1):
            break


        #If "root" is used, then that is also accepted by the API
        #the restriction is that it doesn't apply to shared documents
        data["q"] = f"((mimeType='application/vnd.google-apps.folder' or mimeType= 'application/vnd.google-apps.document') and  \
                trashed = False) and ('{proc_file.id}' in parents)"

        # Enable shared drive finding
        data["q"] = f"((mimeType='application/vnd.google-apps.folder' or mimeType= 'application/vnd.google-apps.document') and  \
                trashed = False)"
        data["q"] = "({}) and modifiedTime > '2016-10-04T12:00:00'".format(data["q"])
        try:
            async with session.get(url=drive_url, params=data,
                                   headers=headers) as response:
                resp = await TestUtil.handleResponse(response)
                if (resp == -1):
                    #If response code is negative, means there is an error, most likely
                    #related to permissions. There is no need to process further
                    continue
        except:
            logger.debug("connection closed prematurely with gdrive ")
            await asyncio.sleep(random.uniform(0, 20))
            continue

        temp_docs = {}

        batch_job = {0: TestUtil.drive.new_batch_http_request() }
        jobs_added = 0


        def last_rev_callback(id, response, exc):
            if exc:
                logger.info("exception in callback", exc_info = exc)
                raise exc
            try:
                temp_docs[id] = temp_docs[id]._replace(last_revision_id = response["revisions"][-1]["id"])
                if id not in tot_files:
                    files.put_nowait(temp_docs[id])
                tot_files[id] = True
            except:
                breakpoint()

        for resFile in resp["files"]:
            id = resFile["id"]

            ent_name = "".join([ "" if c in {'\'', '\\', '"', "'"} else c for c in resFile["name"]]) \
                    .rstrip()[0:298]

            f = temp_file(name=ent_name,
                          id=id,
                          path=proc_file.path + [(id, ent_name)],
                          type=resFile["mimeType"],
                          last_revision_id = None)

            if (resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put(f)
            elif (resFile["mimeType"] == ACCEPTED_TYPES):
                # First element id is not used for naming, only for api calls
                if not resFile["capabilities"]["canReadRevisions"] or id in tot_files:
                    continue

                temp_docs[f.id]=f
                
                jobs_added += 1

                idx = int(jobs_added / 20)
                print("idx: ", idx)
                print("fold size: ", folders.qsize())

                if idx not in batch_job:
                    batch_job[idx] = TestUtil.drive.new_batch_http_request() 

                batch_job[idx].add(TestUtil.drive.revisions().list(fileId = f.id, fields = "revisions(id)", pageSize = 1000), request_id = f.id,
                        callback = last_rev_callback)


        for jobs in batch_job.values():
            i = 0
            while True:
                while stop():
                    await asyncio.sleep(20)
                i += 1
                try:
                    jobs.execute()
                    logger.info("Batch job execution succeeded, going to next job")
                    break
                except Exception as e:
                    logger.info("Batch job executio failed!")
                    await asyncio.sleep(i*25)
                    

            
            

    collection_done.set()
    logger.info("getid return, len %d:%d:%d", TestUtil.processedcount,
                files.qsize(), len(TestUtil.files))


async def shutdown_task(endEvent):
    await endEvent.wait()

    logger.info("sleeping  before shutting down")
    await asyncio.sleep(4)
    await shutdown()
    logger.info("shutting tasks done")

#@profile
async def getRevision(files,
                      session: aiohttp.ClientSession,
                      headers,
                      endEvent,
                      name='default'):

    # Await random amount for more staggered requesting, and to allow queryDriveActivity
    # time to fill the files queue with jobs

    while files.empty() and not endEvent.is_set():
        await asyncio.sleep(random.uniform(0, 6))

    while not endEvent.is_set():
        proc_file = await tryGetQueue(files, name="getRevision", interval=10, repeatTimes = 3, endEvent = endEvent)

        if (proc_file == -1 ):
            if not collection_done.is_set():
                await asyncio.sleep(20)
                continue
            else:
                logger.warning('getRevision task exiting')
                break
        gd = GDoc()
        await gd.file_async_init(proc_file, session, TestUtil.headers)

        if gd.done and gd.operations:
            TestUtil.files.append(gd)
            print("done proessed ", gd.name)


    endEvent.set()
    logger.info("getrev return")

    return


async def start():

    logger.info("THREADS: {} WORKERS: {}".format(gdoc.threads, workerInstances))

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)

    folders = asyncio.Queue()
    files = asyncio.Queue()

    #Initialize the first folder to be put in.
    first_folder = temp_file(name='root',
                             id=SEED_ID,
                             type='',
                             path=[('root', 'root')],
                             last_revision_id = None)

    await folders.put(first_folder)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Generate list of Workers to explore folder structure

        endEvent = asyncio.Event()

        logger.info("Creating tasks")

        printTask = loop.create_task(TestUtil.print_size(files, endEvent))

        #asyncio.create_task(gat(printTask))

        fileExplorers = [loop.create_task(getIdsWrapper("https://www.googleapis.com/drive/v3/files", \
                                         folders, files, session, TestUtil.headers, endEvent)) for i in range(1)]
        #asyncio.create_task(gat(fileExplorers[0]))

        loop.create_task(shutdown_task(endEvent))


        revisionExplorer = []

        while files.qsize() < 5:
            # Let the producer task have some leeway
            await asyncio.sleep(2)

        for i in range(workerInstances):
            revisionExplorer.append(
                loop.create_task(getRevision(files, session, TestUtil.headers, endEvent)))
            await asyncio.sleep(1.5)

        await asyncio.gather(*revisionExplorer, *fileExplorers, printTask)


    printTask.cancel()
    logger.info("start() task done")


def exchandler(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")
    asyncio.create_task(shutdown(loop))


async def shutdown(loop = None, signal=None):
    if signal:
        logging.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    if loop:
        loop.stop()


def loadFiles(USER_ID, _workingPath, fileId, _creds):
    #Program starting point
    logger.info("Start loadFiles, %s %s", USER_ID, fileId)

    #_workingPath is deprecated, TODO: remove _workingPath
    _workingPath = os.environ["HOMEDATAPATH"]

    #Set the unique token for logging. This helps to differentiate between multiple simultaneous workers
    configlog.set_token(USER_ID)

    Path(_workingPath).mkdir(exist_ok=True)

    # Load pickle file. Should have been made by Flask/App.py
    # in authorization step
    TestUtil.refresh_creds(_creds)
    TestUtil.workingPath = _workingPath
    TestUtil.userid = USER_ID


    if (fileId != None):
        global SEED_ID
        SEED_ID = fileId

        #TODO: query GDrive to find out the actual filename of the root fileId, to
        #be done in queryDriveActivity or start()?

    # Main loop
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    startTask = loop.create_task(start())

    try:
        loop.run_until_complete(asyncio.gather(startTask))
    except asyncio.CancelledError:
        pass


    # Writing data to SQL
    import processing.sql
    files =  TestUtil.dump_files()
    processing.sql.start(USER_ID, files.files, upload=True)

    logger.info("Program ended successfully for userid %s", USER_ID)
