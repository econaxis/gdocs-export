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
import math
from googleapiclient.discovery import build
import pandas as pd
import iso8601
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path


#Imports TestUtil and corresponding functions
from processing.datutils.test_utils import *

pp = pprint.PrettyPrinter(indent=4);

class FilePrintText:
    text = ""

    @classmethod
    def add(cls, txt):
        cls.text +=txt + "<br>"

    @classmethod
    def clear(cls):
        cls.text = ""


lastModFile = {}

docs = []

MAX_FILES = 20000
collapsedFiles = {}
pathedFiles = {}

acThrottle = None
drThrottle = None

SEED_ID = "root"

workerInstances = 3

ACCEPTED_TYPES = {"application/vnd.google-apps.presentation", "application/vnd.google-apps.spreadsheet", "application/vnd.google-apps.document", "application/vnd.google-apps.file", "application/pdf"}




async def getIdsRecursive(drive_url, folders: asyncio.Queue, 
        files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    global MAX_FILES, lastModFile, drThrottle
    
    #Wait random moment for folder queue to be populated
    await asyncio.sleep(random.randint(0, 3))

    #Query to pass into Drive to find item

    while (files.qsize() + len(lastModFile) < MAX_FILES):
        #Wait for folders queue, with interval 6 seconds between each check
        #Necessary if more than one workers all starting at the same time,
        #with only one seed ID to start
        #await drThrottle.sem.acquire()
        folderIdTuple = await tryGetQueue(folders, name = "getIds", interval = 3)

        if(folderIdTuple == -1):
            return
        (id, path, retries) = folderIdTuple

        #Root id is different structure
        data = None
        if(id == "root"):
            data = dict(corpora="allDrives", includeItemsFromAllDrives = 'true',
                    supportsTeamDrives = 'true')
        else:
            query = "'" + id + "' in parents"
            data = dict(q=query, corpora = "allDrives",
                    includeItemsFromAllDrives = 'true', supportsTeamDrives = 'true')


        try:
            async with session.get(url = drive_url, params = data, headers = headers) as response:
                resp = await handleResponse(response, folders, folderIdTuple, advanced = False)
                if(resp == -1):
                    continue
        except aiohttp.client_exceptions:
            print("something wrong with session.get connection closed prematurely?")
            continue



        #Parse file and folder names to make them filesystem safe, limit to 120 characters
        ent_name = "".join(["" for c in resFile["name"] if c in ['\"', '\'', '\\']]).rstrip()[0:119]


        for resFile in resp["files"]:
            if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                await folders.put([resFile["id"], path + [ent_name], 0] )
            elif (resFile["mimeType"] in ACCEPTED_TYPES):
                await files.put([resFile["id"], ent_name, resFile["mimeType"],path + [ent_name], 0])

        folders.task_done()


    #Check valid
    while(not folders.empty()):
        folders.get_nowait()
        folders.task_done()
    print("get ID task done")
    #Folder Size exceeded therefore, get all and clear all elements out of queue
    #Folders for blocking call q.join() to be released


async def queryDriveActivity(fileTuple, files, session, headers):

    (fileId, fileName, kind, path, tried) = fileTuple

    revisions  = {}
    rev = None
    act = None
    async with session.get(url = dr2_urlbuilder(fileId), headers = headers) as revResponse:
        code = await handleResponse(revResponse, files, fileTuple)
        if code == -1:
            return
        else:
            revisions = code

    async with session.post(**TestUtil.dractivity_builder(fileId)) as actResponse:
        code = await handleResponse(actResponse, files, fileTuple)
        if code == -1:
            return
        else:
            act = code

    acThrottle.increase()

    if(not revisions.get("items")):
        return

    revisions = revisions["items"]
    for item in revisions:
        modifiedDate = iso8601.parse_date(item["modifiedDate"])
        collapsedFiles[(fileName,  modifiedDate)] = 1
        pathedFiles [(*path,)] = modifiedDate


        lastModFile[(fileName, fileId)] = modifiedDate


    act = act.get("activities", [dict(timestamp = "2019-03-13T01:34:24.629Z")])
    for a in act:
        revisions.append(dict(modifiedDate = a["timestamp"]))

    files.task_done()

async def handleResponse(response, queue, fileTuple, advanced = True):
    try:
        rev = await response.json()
        assert response.status == 200, "Response not 200"
    except:
        e = sys.exc_info()[0]
        rev = await response.text()
        TestUtil.errors(e)
        TestUtil.errors(rev)

        if advanced:
            await API_RESET(throttle = acThrottle, decrease = True)
        else:
            await API_RESET(throttle = acThrottle, decrease = False)

        if(fileTuple[-1] < 3):
            fileTuple[-1] +=1
            await queue.put(fileTuple)

        return -1
    return rev


async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    #Await random amount for more staggered requesting (?)
    await asyncio.sleep(random.randint(0, 15))
    s = time.time()
    while True:
        await acThrottle.acquire()

        #Random code to reset counter every 2/10 times 
        fileTuple = await tryGetQueue(files, name = "getRevision")
        if(fileTuple==-1):
            return

        (fileId, fileName, kind, path, tried) = fileTuple

        FilePrintText.add(fileId[0:3] + " <i>" + '/'.join(path) + "</i>")

        if(kind != "application/vnd.google-apps.document" or True):
            await queryDriveActivity(fileTuple, files, session, headers)
        else:
            print('='*10, fileId, TestUtil.creds, '='*10)
            docs.append(gdr.GoogleDoc(fileId, TestUtil.creds))
            print(len(docs), "len")

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly', 'https://www.googleapis.com/auth/drive']

async def start():
    global SEED_ID, workerInstances, lastModFile, acThrottle, drThrottle
    
    acThrottle = Throttle(80)
    drThrottle = Throttle(100)
    TestUtil.throttle = acThrottle

    async with aiohttp.ClientSession() as session:
        folders = asyncio.Queue()
        files = asyncio.Queue()


        #Seed ID to start initial folder requests
        #Limits recursion limit
        await folders.put([SEED_ID, ["root"], 0] )

        tt = asyncio.create_task(acThrottle.work())
        #dd = asyncio.create_task(drThrottle.work())
        #Generate list of Workers to explore folder structure
        fileExplorers = [asyncio.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files",
            folders, files, session, TestUtil.headers)) for i in range(workerInstances)]

        revisionExplorer = [asyncio.create_task(getRevision(files, session, TestUtil.headers))
            for i in range(workerInstances)]

        #Generate Print Task that prints data every X seconds
        printTask = asyncio.create_task(TestUtil.print_size(files, lastModFile, FilePrintText))
        #Wait until all folders are properly processed, or until FILE_MAX is reached
        jobs = asyncio.gather(*(fileExplorers + revisionExplorer))



        await jobs
        tt.cancel()
#        dd.cancel()
        printTask.cancel()
        print("cancelled throttler")




def loadFiles(USER_ID, _workingPath, fileId, _creds):
    Path(_workingPath).mkdir(exist_ok = True)

    print("load files started")
    print("USER ID: %s"%USER_ID, " ", fileId)

    #Load pickle file. Should have been made by Flask/App.py
    #in authorization step

    TestUtil.refresh_creds(_creds)
    TestUtil.workingPath = _workingPath


    if(fileId != None):
        global SEED_ID
        SEED_ID = fileId

    #Main loop
    asyncio.run(start(), debug = True)


    d = set()
    for l1 in pathedFiles:
        for i1, path in enumerate(l1):
            path2 = l1[-1]
            d.update([(path, path2, len(l1)-i1)])

    pickle.dump(d, open(_workingPath + 'closure.pickle', 'wb'))
    pickle.dump(collapsedFiles, open(_workingPath + 'collapsedFiles.pickle', 'wb'))
    pickle.dump(pathedFiles, open(_workingPath + 'pathedFiles.pickle', 'wb'))
    pickle.dump(docs, open(_workingPath + 'docs.pickle', 'wb'))



    if(len(collapsedFiles) == 0 or len(pathedFiles) == 0):
        return "No files found for this id. check invalid"


    TestUtil.formatData()

    TestUtil.activity_gen()

    #Writing data to SQL
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
