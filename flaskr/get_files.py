import asyncio
import time
import random
import json
import os
import uuid
import pickle
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
from flaskr.datutils.test_utils import *

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
MAX_FILES = 20000
ENABLE_FILESIZE = False
collapsedFiles = {}
pathedFiles = {}

consecutiveErrors = 1

SEED_ID = "root"

workerInstances = 3

def exceptionHandler(loop, context):
    #loop.default_exception_handler(context)
    print("="*10)
    exception = context.get('exception')
    print("exception: %s"%exception)
    print("loop %s"%loop)
    print("=" * 20)
    loop.stop()


async def getIdsRecursive(drive_url, folders: asyncio.Queue, files: asyncio.Queue, 
    session: aiohttp.ClientSession, headers):

    global MAX_FILES, lastModFile
    
    #Wait random moment for folder queue to be populated
    await asyncio.sleep(random.randint(0, 10))

    #Query to pass into Drive to find item

    while (files.qsize() + len(lastModFile) < MAX_FILES):
        print(1)
        #Wait for folders queue, with interval 6 seconds between each check
        #Necessary if more than one workers all starting at the same time,
        #with only one seed ID to start
        folderIdTuple = await tryGetQueue(folders, name = "getIds", interval = 3)
        if(folderIdTuple == -1):
            return
        (id, path) = folderIdTuple
        query = "'" + id + "' in parents"
        data = dict(q=query)
        async with session.get(url = drive_url, params = data, headers = headers) as response:

            if(response.status != 200):
                #Checks if passed GDrive limit
                if(response.status == 403):
                    print("Waiting for GDrive API Limit...")
                    FilePrintText.add("Waiting for GDrive API Limit...")
                    pp.pprint(await response.text())
                    #Reset, add ID back to queue as this item will not be processed
                    await folders.put(folderIdTuple)
                else:
                    print("Not 403, But Error")
                    print(await response.text())
                await API_RESET(FilePrintText)
            else:
                global consecutiveErrors
                consecutiveErrors = 1
                DriveResponse = await response.json()


                #Classify item type by file or folder
                #If folder, then add back to folder queue for further processing
                for resFile in DriveResponse["files"]:
                    if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                        await folders.put( (resFile["id"], path + [resFile["name"]]) )
                    elif (resFile["mimeType"] == "application/vnd.google-apps.document"):
                        await files.put((resFile["id"], resFile["name"], path + [resFile["name"]]))


        #Mark task as done for folders.join() to properly work
        folders.task_done()

    while(not folders.empty()):
        folders.get_nowait()
        folders.task_done()
    print("get ID task done")
    #Folder Size exceeded therefore, get all and clear all elements out of queue
    #Folders for blocking call q.join() to be released


async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers):
    #Await random amount for more staggered requesting (?)
    await asyncio.sleep(5 + random.randint(0, 10))
    while True:
        print(1)
        fileTuple = await tryGetQueue(files, name = "getRevision")
        if(fileTuple==-1):
            return

        (fileId, fileName, path) = fileTuple

        FilePrintText.add(fileId[0:3] + " <i>" + '/'.join(path) + "</i>")


        revisions  = {}
        async with session.get(url = dr2_urlbuilder(fileId), headers = headers) as revResponse:
            async with session.post(**TestUtil.dractivity_builder(fileId)) as actResponse:
                if(revResponse.status != 200 or actResponse.status != 200):
                    #Checks if passed GDrive limit
                    if(revResponse.status == (403 or 429) or actResponse.status == (403 or 429)):
                        print("Waiting for GDrive API Limit...")
                        FilePrintText.add("Waiting for GDrive API Limit...")
                        #Reset, add ID back to queue
                        await files.put(fileTuple)
                    else:
                        print("non 403 error")
                        #Assuming revResponse does not violate quota
                        print(await actResponse.text())

                        open("errors.txt", 'a').write(await revResponse.text() + await actResponse.text())
                    await API_RESET(FilePrintText)
                else:
                    consecutiveErrors=1
                    revisions = await revResponse.json()
                    revisions = revisions["items"]

                    act = await actResponse.json()
                    act = act["activities"]

                    #Append activities gained through driveactivity in structure "act"
                    #to revisions, which can be processed all in one by following code
                    for a in act:
                        revisions.append(dict(modifiedDate = a["timestamp"]))
        for item in revisions:
            global ENABLE_FILESIZE

            modifiedDate = iso8601.parse_date(item["modifiedDate"])


            '''
            if(ENABLE_FILESIZE and "fileSize" in item):
                collapsedFiles[(fileName,  modifiedDate)] = int(item["fileSize"])
                pathedFiles [(*path[0:recursionSize], modifiedDate)] = int(item["fileSize"])
            else:
                collapsedFiles[(fileName,  modifiedDate)] = 1
                pathedFiles [(*path, modifiedDate)] = 1
            '''
            collapsedFiles[(fileName,  modifiedDate)] = 1
            pathedFiles [(*path, modifiedDate)] = 1


            lastModFile[fileName] = modifiedDate

        files.task_done()

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly'] 

async def start():
    global SEED_ID, workerInstances, lastModFile



    async with aiohttp.ClientSession() as session:
        folders = asyncio.Queue()
        files = asyncio.Queue()


        #Seed ID to start initial folder requests
        #Limits recursion limit
        await folders.put(( SEED_ID, ["root"]) )


        #Generate list of Workers to explore folder structure
        fileExplorers = [asyncio.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files",
            folders, files, session, TestUtil.headers)) for i in range(workerInstances)]

        revisionExplorer = [asyncio.create_task(getRevision(files, session, TestUtil.headers))
            for i in range(workerInstances)]

        #Generate Print Task that prints data every X seconds
        printTask = asyncio.create_task(TestUtil.print_size(files, lastModFile, FilePrintText))
        #Wait until all folders are properly processed, or until FILE_MAX is reached
        jobs = asyncio.gather(*(fileExplorers + revisionExplorer))

        print("jobs started")
        await jobs
        print("All jobs done")

        #Cancel because Done
        for i in fileExplorers:
            i.cancel()
        for i in revisionExplorer:
            i.cancel()

        printTask.cancel()



def loadFiles(USER_ID, _workingPath, fileId, _creds):

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

    pickle.dump(collapsedFiles, open(_workingPath + 'collapsedFiles.pickle', 'wb'))
    pickle.dump(pathedFiles, open(_workingPath + 'pathedFiles.pickle', 'wb'))




    TestUtil.formatData()

    TestUtil.activity_gen()

    open(_workingPath + 'done.txt', 'a+').write("DONE")
 #   asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy

if __name__ == "__main__":

    #Default settings
    uid = "5a80b6d0-07bb-42c2-a023-15894be46026"
    homePath =  "/mnt/c/users/henry/documents/pydocs/"
    TestUtil.workingPath =  homePath + 'data/' + uid + '/'
    loadFiles(uid, TestUtil.workingPath)
