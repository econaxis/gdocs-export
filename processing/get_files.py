import asyncio
from collections import namedtuple
import random
import aiohttp
import pprint
from pathlib import Path
import logging
import configlog

# Imports TestUtil and corresponding functions
from processing.datutils.test_utils import TestUtil, os, tryGetQueue
from processing.gdoc import GDoc

logger = logging.getLogger(__name__)

pprint = pprint.PrettyPrinter(indent=4).pprint

timeout = aiohttp.ClientTimeout(total=15)

SEED_ID = "root"

workerInstances = 5

ACCEPTED_TYPES = {"application/vnd.google-apps.document"}

temp_file = namedtuple('temp_file', ['id', 'name', 'type', 'path'])

#For managing duplicates
tot_folders = {}


async def getIdsRecursive(drive_url, folders: asyncio.Queue,
                          files: asyncio.Queue, session: aiohttp.ClientSession,
                          headers, done_event):

    # This is the common data-dict to be passed into all our HTTP requests.
    # We need to fill out the q variable, depending on the folder id being requested
    data = dict(
        q="",
        corpora="allDrives",
        includeItemsFromAllDrives='true',
        supportsTeamDrives='true',
        fields=
        'files/mimeType, files/id, files/name, files/capabilities/canReadRevisions',
        pageSize=1000)
    # Query to pass into Drive to find item

    while not done_event.is_set():
        # Wait for folders queue, with interval 6 seconds between each check
        # Necessary if more than one workers all starting at the same time,
        # with only one seed ID to start

        # Deprecated, do not need to throttle google drive api
        # await drThrottle.sem.acquire()

        proc_file = await tryGetQueue(folders,
                                      name="getIds",
                                      interval=3,
                                      repeatTimes=5)

        if (proc_file == -1):
            break

        query = "((mimeType='application/vnd.google-apps.folder' or mimeType= 'application/vnd.google-apps.document') and  \
                trashed = False)"

        #If "root" is used, then that is also accepted by the API
        #the restriction is that it doesn't apply to shared documents
        query += f"and ('{proc_file.id}' in parents)"

        # We replace the existing data template with our own query.
        data["q"] = query

        try:
            async with session.get(url=drive_url, params=data,
                                   headers=headers) as response:
                resp = await TestUtil.handleResponse(response)
                if (resp == -1):
                    #If response code is negative, means there is an error, most likely
                    #related to permissions. There is no need to process further
                    continue
        except:
            #This should not throw an error because GDrive API limits are much higher, and
            #there is no way we can exceed this limit
            secs = random.uniform(5, 20)
            logger.exception(
                "connection closed prematurely with gdrive, sleeping for %d",
                secs)
            await asyncio.sleep(secs)
            continue

        for resFile in resp["files"]:
            id = resFile["id"]

            ent_name = "".join([ "" if c in {'\'', '\\', '"', "'"} else c for c in resFile["name"]]) \
                    .rstrip()[0:298]

            f = temp_file(name=ent_name,
                          id=id,
                          path=proc_file.path + [(id, ent_name)],
                          type=resFile["mimeType"])

            if (resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put(f)
            elif (resFile["mimeType"] in ACCEPTED_TYPES):

                # DEBUGGING
                # Testing paths, force all files to be part of SOME folder

                if len(f.path) <= 2 and "FLASKDBG" in os.environ:
                    #There is no pathing, so we ignore. For debugging only
                    continue

                # First element id is not used for naming, only for api calls
                if not resFile["capabilities"][
                        "canReadRevisions"] or id in tot_folders:
                    continue
                tot_folders[id] = True
                await files.put(f)

    logger.info("getid return, len %d:%d:%d", TestUtil.processedcount,
                files.qsize(), len(TestUtil.files))


async def getRevision(files,
                      session: aiohttp.ClientSession,
                      headers,
                      endEvent,
                      name='default'):

    # Await random amount for more staggered requesting, and to allow queryDriveActivity
    # time to fill the files queue with jobs
    await asyncio.sleep(
        random.uniform(workerInstances * 1, workerInstances * 1.5))

    while not endEvent.is_set():
        proc_file = await tryGetQueue(files, name="getRevision", interval=4)

        if (proc_file == -1):
            logger.warning('getRevision task exiting')
            break

        logger.debug("%s path: %s", proc_file.name,
                     list(zip(*proc_file.path))[1])

        gd = GDoc()
        await gd.async_init(proc_file.name, proc_file.id, session,
                            TestUtil.headers, proc_file.path)

        if gd.done and gd.operations:
            TestUtil.files.append(gd)
        else:
            logger.debug(
                "not done but tried to append, prob because no operations found file: %s, %s %s %s",
                gd.fileId, gd.name, gd.done, gd.operations)

    endEvent.set()
    logger.info("getrev return")

    return


async def start():

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    #loop.set_debug(True)
    """
    #Debugging set at 0, we don't need the SQLSERVER
    socket_tries = 0
    while socket_tries:
        try:
            ex = Info(extra="testing extra function from start()")
            await TestUtil.test_server(ex)
        except:
            logger.info("Starting socket send failed, retrying after 2s")
            socket_tries -=1
            await asyncio.sleep(2)
        else:
            socket_tries = 1
            break
    TestUtil.sql_server_active = bool(socket_tries)
    """

    TestUtil.sql_server_active = False

    folders = asyncio.Queue()
    files = asyncio.Queue()

    #Initialize the first folder to be put in.
    first_folder = temp_file(name='root',
                             id=SEED_ID,
                             type='',
                             path=[('root', 'root')])
    await folders.put(first_folder)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Generate list of Workers to explore folder structure

        endEvent = asyncio.Event()

        fileExplorers = [loop.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files", \
                                         folders, files, session, TestUtil.headers, endEvent)) for i in range(1)]

        revisionExplorer = [
            loop.create_task(
                getRevision(files, session, TestUtil.headers, endEvent))
            for i in range(workerInstances)
        ]

        # Generate Print Task that prints data every X seconds, useful for debugging and viewing progress
        printTask = loop.create_task(TestUtil.print_size(files, endEvent))

        # asyncio.gather is necessary for exception handling.
        # if we don't gather, then exceptions propagated in these three tasks will be swallowed
        await asyncio.gather(*revisionExplorer, *fileExplorers, printTask)

    await TestUtil.dump_files(upload=True)

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
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks]

    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    logging.info("Emailing logs...")
    sendmail()
    logging.info("Stopping")
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
        TestUtil.idmapper[SEED_ID] = 'root'

    # Main loop
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exchandler)
    startTask = loop.create_task(start())

    loop.run_until_complete(asyncio.gather(startTask))

    if not TestUtil.sql_server_active:
        # Writing data to SQL
        import processing.sql
        processing.sql.start(USER_ID,
                             TestUtil.info.files,
                             upload=True,
                             create_new=True)

    open(_workingPath + 'done.txt', 'a+').write("DONE")
    configlog.sendmail(msg="program ended successfully")

    #pickle.dump(TestUtil.dbg_infos, open('dbg_infos', 'wb'))
    logger.info("Program ended successfully for userid %s", USER_ID)
