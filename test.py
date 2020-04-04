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
pp = pprint.PrettyPrinter(indent=4);


homePath = None
headers = {}
lastModFile = {}
MAX_FILES = 50
ENABLE_FILESIZE = False
revData = {}
creds = 0
consecutiveErrors = 1

SEED_ID = "0B4Fujvv5MfqbeTVRc3hIbXRfNE0"
g_USER_ID = str(uuid.uuid4())
USER_ID = "default"

workerInstances = 3

def API_RESET(seconds = 10):
    global consecutiveErrors
    consecutiveErrors+=1
    seconds *=(consecutiveErrors+1)
    for i in range(math.ceil(seconds/10)):
        print(consecutiveErrors)
        print("%d/%d"%(i, math.ceil(seconds/10)))
        time.sleep(10)


def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

def dractivity_builder(id):
    global headers
    ancName = "items/" + id
    pageSize = 1000
    filter = "detail.action_detail_case: EDIT"

    #Generate random quotaUser
    quotaUser = str(uuid.uuid4())

    params = dict(ancestorName = ancName, pageSize = pageSize, 
        filter = filter, quotaUser = quotaUser)
    return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")

async def print_size(folder, file):
    while True:
        outputString = "FLDR SZ: %d FILE SZ: %d\n" %(folder.qsize(), file.qsize())

        streamingFile = open(homePath + "streaming.txt", 'a')
        streamingFile.write(outputString)
        print(outputString)
        
        await asyncio.sleep(3)

async def getIdsRecursive(drive_url, folders: asyncio.Queue, files: asyncio.Queue, 
    session: aiohttp.ClientSession, headers: dict):
    global MAX_FILES, lastModFile

    await asyncio.sleep(0, workerInstances)
    #Query to pass into Drive to find item

    #files q size for un processed files, lastModFile for processed files
    while (files.qsize() + len(lastModFile) < MAX_FILES):
        id = await folders.get()
        query = "'" + id + "' in parents"
        data = dict(q=query)
        async with session.get(url = drive_url, params = data, headers = headers) as response:
            if(response.status != 200):
                #Checks if passed GDrive limit
                if(response.status == 403):
                    print("Waiting for GDrive API Limit...")
                    #Reset, add ID back to queue as this item will not be processed
                    await folders.put(id)
                else:
                    print("Not 403, But Error")
                    print(await response.text())
                API_RESET()
            else:
                global consecutiveErrors
                consecutiveErrors = 1
                DriveResponse = await response.json()


                #Classify item type by file or folder
                #If folder, then add back to folder queue for further processing
                for resFile in DriveResponse["files"]:
                    if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                        await folders.put(resFile["id"])
                    elif (resFile["mimeType"] == "application/vnd.google-apps.document"):
                        await files.put((resFile["id"], resFile["name"]))

        #Mark task as done for folders.join() to properly work
        folders.task_done()
    #Folder Size exceeded therefore, get all and clear all elements out of queue
    #Folders for blocking call q.join() to be released
    while (await folders.get()):
        folders.task_done()

async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers):

    #Await random amount for more staggered requesting (?)
    await asyncio.sleep(0, workerInstances)

    while True:
        fileId, fileName = await files.get()
        print(fileId, fileName)

        revisions  = {}
        async with session.get(url = dr2_urlbuilder(fileId), headers = headers) as revResponse:
            async with session.post(**dractivity_builder(fileId)) as actResponse:
                if(revResponse.status != 200 or actResponse.status != 200):
                    #Checks if passed GDrive limit
                    if(revResponse.status == 403 or actResponse.status == 403):
                        print("Waiting for GDrive API Limit...")
                        #Reset, add ID back to queue
                        await files.put(fileId)
                    else:
                        print("non 403 error")
                        #Assuming revResponse does not violate quota
                        print(await actResponse.text())

                        open("errors.txt", 'a').write(await revResponse.text() + await actResponse.text())                       
                    API_RESET()
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

            if(ENABLE_FILESIZE and "fileSize" in item):
                revData[(fileName,  modifiedDate)] = int(item["fileSize"])
            else:
                revData[(fileName,  modifiedDate)] = 1

            lastModFile[fileName] = modifiedDate
        files.task_done()






SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']

async def start(creds):
    global SEED_ID, workerInstances, headers

    creds.apply(headers)
    async with aiohttp.ClientSession() as session:
        folders = asyncio.Queue()
        files = asyncio.Queue()


        #Seed ID to start initial folder requests
        await folders.put(SEED_ID)


        #Generate list of Workers to explore folder structure
        fileExplorers = [asyncio.create_task(getIdsRecursive("https://www.googleapis.com/drive/v3/files", 
            folders, files, session, headers)) for i in range(workerInstances)]

        revisionExplorer = [asyncio.create_task(getRevision(files, session, headers)) 
            for i in range(workerInstances)]

        #Generate Print Task that prints data every X seconds
        printTask = asyncio.create_task(print_size(folders, files))

        #Wait until all folders are properly processed, or until FILE_MAX is reached
        p = await folders.join()
        p = await files.join()

        #Cancel because Done
        for i in fileExplorers:
            i.cancel()
        for i in revisionExplorer:
            i.cancel()

        printTask.cancel()
        pickle.dump(revData, open('revdata.pickle', 'wb'))


def main(USER_ID, pydocPath):
    global creds, homePath

    homePath = pydocPath

    DIR = pydocPath + "data/" + USER_ID + "/"
    p = Path(DIR)
    p.mkdir(exist_ok = True)
    os.chdir(DIR)

    print("USER ID: %s"%USER_ID)

    #Load pickle file. Should have been made by Flask/App.py
    #in authorization step

    with open('creds.pickle', 'rb') as cr:
        creds = pickle.load(cr)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise "Creds not valid!"
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)




    print("file loaded", USER_ID)

    asyncio.run(start(creds), debug = True)


    from datutils import formatData, activity_gen
    formatData()

    activity_gen()
 #   asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy

if __name__ == "__main__":
    import datutils


    main("c4004ebc-ac00-401b-a17b-01f614325b0f", "/mnt/c/users/henry/documents/pydocs/")
