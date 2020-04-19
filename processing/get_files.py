import asyncio
import gdocrevisions as gdr
import sys
from time import time
from datetime import datetime
import random
import json
import os
import uuid
import pickle
from processing.throttler import Throttle
import aiohttp
import pprint
from googleapiclient.discovery import build
import pandas as pd
import iso8601
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path


# Imports TestUtil and corresponding functions
from processing.datutils.test_utils import *

pprint = pprint.PrettyPrinter(indent=4).pprint


class FilePrintText:
    text = ""

    @classmethod
    def add(cls, txt):
        cls.text += txt + "<br>"

    @classmethod
    def clear(cls):
        cls.text = ""


# Deprecated

docs = []

MAX_FILES = 20000
pathedFiles = {}
idmapper = {}

acThrottle = None

SEED_ID = "root"

workerInstances = 10

ACCEPTED_TYPES = { "application/vnd.google-apps.presentation", "application/vnd.google-apps.spreadsheet", "application/vnd.google-apps.document", "application/pdf"}


async def getIdsRecursive (drive_url, folders: asyncio.Queue,
                          files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    global MAX_FILES
    # Wait random moment for folder queue to be populated
    await asyncio.sleep(random.uniform(0, 4))

    # Query to pass into Drive to find item

    while (files.qsize() + len(pathedFiles) < MAX_FILES):
        # Wait for folders queue, with interval 6 seconds between each check
        # Necessary if more than one workers all starting at the same time,
        # with only one seed ID to start

        # Deprecated, do not need to throttle google drive api
        # await drThrottle.sem.acquire()

        await asyncio.sleep(random.uniform(0, 2))

        folderIdTuple = await tryGetQueue(folders, name="getIds", interval=3)

        if(folderIdTuple == -1):
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
                resp = await handleResponse(response, folders, folderIdTuple, decrease=False)
                if(resp == -1):
                    continue
        except aiohttp.client_exceptions:
            print("something wrong with session.get connection closed prematurely?")
            continue

        # Parse file and folder names to make them filesystem safe, limit to
        # 120 characters

        global idmapper
        for resFile in resp["files"]:
            ent_name = "".join(["" if c in ['\"', '\'', '\\']
                        else c for c in resFile["name"]]).rstrip()[0:298]
            id = resFile["id"]
            idmapper[id[0:44]] = ent_name
            if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put((id, path + [id[0:44]], 0))
            elif (resFile["mimeType"] in ACCEPTED_TYPES):
                # First element id is not used for naming, only for api calls
                await files.put([id, resFile["mimeType"], path + [id[0:44]], 0])


async def queryDriveActivity(fileTuple, files, session, headers):

    (fileId, mimeType, path, tried) = fileTuple

    async with session.get(url=dr2_urlbuilder(fileId), headers=headers) as revResponse:
        code = await handleResponse(revResponse, files, fileTuple)
        if code == -1:
            _revisions = dict()
        else:
            _revisions = code

    async with session.post(**TestUtil.dractivity_builder(fileId)) as actResponse:
        code = await handleResponse(actResponse, files, fileTuple, decrease=True)
        if code == -1:
            return -1
        else:
            activities = code
            acThrottle.increase()

    # No items will be found if the first drive revision returns an error
    # This occurs when the user doesn't have permission
    _revisions = _revisions.get('items', [])

    activities = activities.get("activities", [])

    for a in activities:
        _revisions.append(dict(modifiedDate=a["timestamp"]))

    for item in _revisions:
        modifiedDate = iso8601.parse_date(item["modifiedDate"])
        if((*path,) not in pathedFiles):
            pathedFiles[(*path,)] = [modifiedDate]
        else:
            pathedFiles[(*path,)].append(modifiedDate)
    return 0


async def handleResponse(response, queue, fileTuple, decrease=True):
    try:
        rev = await response.json()
        assert response.status == 200, "Response not 200"
        return rev
    except BaseException:
        e = sys.exc_info()[0]
        rev = await response.text()
        TestUtil.errors(e)
        TestUtil.errors(rev)

        if response.status == 429:
            await API_RESET(throttle=acThrottle, decrease=True)
        else:
            print('e', end="-")

        if(fileTuple[-1] < 2):
            fileTuple = list(fileTuple)
            fileTuple[-1] += 1
            await queue.put(fileTuple)

        return -1


async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    # Await random amount for more staggered requesting (?)
    await asyncio.sleep(random.uniform(0, 6))
    while True:
        await acThrottle.acquire()

        fileTuple = await tryGetQueue(files, name="getRevision")
        if(fileTuple == -1):
            return

        (fileId, mimeType, path, tried) = fileTuple

        FilePrintText.add(fileId[0:3] + " <i>" + '/'.join(path) + "</i>")

        if(mimeType != "application/vnd.google-apps.document"):
            await queryDriveActivity(fileTuple, files, session, headers)
        else:
            print(2)
            docs.append(gdr.GoogleDoc(fileId, TestUtil.creds))

            for revision in docs[-1].revisions:
                modifiedDate = revision.time
                if((*path,) not in pathedFiles):
                    pathedFiles[(*path,)] = [modifiedDate]
                else:
                    pathedFiles[(*path,)].append(modifiedDate)



async def start():
    global acThrottle

    acThrottle = Throttle(80)
    TestUtil.throttle = acThrottle

    folders = asyncio.Queue()
    files = asyncio.Queue()
    await folders.put([SEED_ID, ["root"], 0])

    tt = asyncio.create_task(acThrottle.work())

    async with aiohttp.ClientSession() as session:
        # Generate list of Workers to explore folder structure
        fileExplorers = [asyncio.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files",
                                                             folders, files, session, TestUtil.headers)) for i in range(workerInstances)]

        revisionExplorer = [asyncio.create_task(getRevision(files, session, TestUtil.headers))
                            for i in range(workerInstances)]

        # Generate Print Task that prints data every X seconds
        printTask = asyncio.create_task( TestUtil.print_size( FilePrintText, pathedFiles, files))
        # Wait until all folders are properly processed, or until FILE_MAX is
        # reached
        jobs = asyncio.gather(*(fileExplorers + revisionExplorer))

        await jobs

    tt.cancel()
    printTask.cancel()
    print("cancelled throttler")


def loadFiles(USER_ID, _workingPath, fileId, _creds):
    Path(_workingPath).mkdir(exist_ok=True)

    print("get_files module\n USER ID: %s" % USER_ID, " ", fileId)

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
    asyncio.run(start(), debug=True)

    d = set()
    for l1 in pathedFiles:
        for i1, path in enumerate(l1):
            path2 = l1[-1]
            d.update([(path, path2, len(l1) - i1 - 1)])

    pickle.dump(d, open(_workingPath + 'closure.pickle', 'wb'))
    pickle.dump(pathedFiles, open(_workingPath + 'pathedFiles.pickle', 'wb'))
    pickle.dump(docs, open(_workingPath + 'docs.pickle', 'wb'))
    pickle.dump(idmapper, open(_workingPath + 'idmapper.pickle', 'wb'))

    if(len(pathedFiles) == 0):
        return "No files found for this id. check invalid"


#    TestUtil.formatData()

#    TestUtil.activity_gen()

    # Writing data to SQL
    import processing.sql
    processing.sql.start(USER_ID, _workingPath)

    open(_workingPath + 'done.txt', 'a+').write("DONE")


 #   asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy
'''
if __name__ == "__main__":
    #Default settings
    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"
    fileid = '0B4Fujvv5MfqbWTE1NF94dmRJVTg'
    homePath =  "/mnt/c/users/henry/pydocs/data/"
    creds = pickle.load(open('creds.pickle', 'rb'))
    TestUtil.workingPath =  homePath + 'data/' + uid + '/'
    loadFiles(uid, TestUtil.workingPath, fileid, creds)
'''
