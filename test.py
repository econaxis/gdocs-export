import asyncio
import time
import random
import json
import os
import pickle
import aiohttp
import pprint
import math
from googleapiclient.discovery import build
import pandas as pd
import iso8601
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
pp = pprint.PrettyPrinter(indent=4);


MAX_FILES = 200
revData = {}

consecutiveErrors = 1

SEED_ID = "0B4Fujvv5MfqbeTVRc3hIbXRfNE0"

workerInstances = 30

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

    ancName = "items/" + id
    pageSize = 1000
    filter = "detail.action_detail_case: EDIT"

    params = dict(ancestorName = ancName, pageSize = pageSize, 
        filter = filter)
    return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")

async def print_size(folder, file):
    while True:
        if(not foldersJoined):
            print("FOLDER SIZE: %d\nFILE SIZE: %d\n"%(folder.qsize(), file.qsize()))
        else:
            print("FILE SIZE: %d\n"%(folder.qsize(), file.qsize()))
        await asyncio.sleep(1.5)

async def getIdsRecursive(drive_url, folders: asyncio.Queue, files: asyncio.Queue, 
    session: aiohttp.ClientSession, headers: dict):
    global MAX_FILES

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
                consecutiveErrors = 1
                DriveResponse = await response.json()

                for resFile in DriveResponse["files"]:
                    if(resFile["mimeType"] == "application/vnd.google-apps.folder"):
                        await folders.put(resFile["id"])
                    elif (resFile["mimeType"] == "application/vnd.google-apps.document"):
                        await files.put((resFile["id"], resFile["name"]))
        folders.task_done()


    #Folder Size exceeded
    #Therefore, get all and clear all elements out of queue
    #Folders for blocking call q.join() to be released
    while (await folders.get()):
        folders.task_done()

async def getRevision(files: asyncio.Queue, session: aiohttp.ClientSession, headers):
    await asyncio.sleep(0, workerInstances)
    while True:
        fileId, fileName = await files.get()
        print(fileId, fileName)

        revisions  = {}
        async with session.get(url = dr2_urlbuilder(fileId), headers = headers) as revResponse:
            async with session.post(**dractivity_builder(fileId)) as actResponse:
                print(1)
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
        print(3)
        for item in revisions:
            modifiedDate = iso8601.parse_date(item["modifiedDate"])
            if(ENABLE_FILESIZE and "fileSize" in item):
                revData[(fileName,  modifiedDate)] = int(item["fileSize"])
            else:
                revData[(fileName,  modifiedDate)] = 1

            lastModFile[fileName] = modifiedDate
        files.task_done()
        print(4)






SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']
async def start():
    global SEED_ID, workerInstances

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
        open("foldersJoined.txt", "a").write("folder")
        d = await files.join()
        open("foldersJoined.txt", "a").write("file")

        #Cancel because Done
        for i in fileExplorers:
            i.cancel()
        for i in revisionExplorer:
            i.cancel()

        printTask.cancel()
        pickle.dump(revData, open('revdata.pickle', 'wb'))


def authorization(fileName = 'secrets/token.pickle', APIKeyPath = 'secret/credentials.json'):
    creds = None

    if os.path.exists(fileName):
        with open(fileName, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                APIKeyPath, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(fileName, 'wb') as token:
            pickle.dump(creds, token)
    return creds


if __name__ == "__main__":
    #creds = authorization()

   # asyncio.run(start(), debug = True)

    from datutils import formatData, activity_gen
    formatData()

    activity_gen()
 #   asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy
