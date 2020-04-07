import asyncio
import time
import uuid
import pickle
import math
from google.auth.transport.requests import Request


creds = None
consecutiveErrors = 0

def creds_from_pickle(path):
    global creds
    with open(path+'creds.pickle', 'rb') as cr:
        creds = pickle.load(cr)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise "Creds not valid!"
        # Save the credentials for the next run
        with open(path + 'token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def API_RESET(seconds = 10):
    global consecutiveErrors
    consecutiveErrors+=1
    seconds *=(consecutiveErrors)
    for i in range(math.ceil(seconds/10)):
        print(consecutiveErrors)
        print("%d/%d"%(i, math.ceil(seconds/10)))
        time.sleep(10)


def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

def dractivity_builder(id):
    headers = {}
    creds.apply(headers)

    ancName = "items/" + id
    pageSize = 1000
    filter = "detail.action_detail_case: EDIT"

    #Generate random quotaUser
    quotaUser = str(uuid.uuid4())

    params = dict(ancestorName = ancName, pageSize = pageSize, 
        filter = filter, quotaUser = quotaUser)
    return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")



async def tryGetQueue(queue: asyncio.Queue, repeatTimes:int = 4, interval:float = 4, name:str = ""):
    output = None
    timesWaited = 0
    while(output==None):
        try:
            timesWaited+=1
            output = queue.get_nowait()
        except:
            if(timesWaited>repeatTimes):
                return -1
            print(name, "  waiting %d / %d"%(timesWaited, repeatTimes))
            await asyncio.sleep(interval)
    return output

async def print_size(folder, file):
    while True:
        outputString = "FLDR SZ: %d FILE SZ: %d\n" %(folder.qsize(), file.qsize())

        streamingFile = open(pydocPath + "streaming.txt", 'a')
        streamingFile.write(outputString)
        print(outputString)
        
        await asyncio.sleep(3)

