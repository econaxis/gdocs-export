import pandas as pd
import numpy as np
import random
from math import log
from datetime import datetime
import google.oauth2.credentials
import google_auth_oauthlib.flow
import asyncio
import time
import uuid
import pickle
import math
from google.auth.transport.requests import Request



class TestUtil:
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']
    creds = None
    headers = {}
    consecutiveErrors = 0
    workingPath = None
    maxSize = 0

    @classmethod
    def formatData(cls, fileName = 'collapsedFiles'):
        rdata = pickle.load(open(cls.workingPath + fileName + '.pickle', 'rb'))

        ind = pd.MultiIndex.from_tuples(rdata.keys())
        data = pd.DataFrame(rdata.values(), index = ind, columns = ["Type"])

        sumDates=data.reset_index(level = 0, drop = True)
        data.to_pickle(cls.workingPath + fileName + "_p.pickle")


    @classmethod
    def activity_gen(cls):
        data = pd.read_pickle(cls.workingPath + 'collapsedFiles_p.pickle')
        hists = {}
        activity = dict(time=[], files=[], marker_size=[])
        for f in data.index.levels[0]:
            timesForFile = data.loc[f].index
            activity["time"].append(data.loc[f].index[-1])
            activity["files"].append(f)
            activity["marker_size"].append(log(len(timesForFile), 1.3))
            hists[f] = [0, 0]
            hists[f][0], bins = np.histogram([i.timestamp() for i in timesForFile], bins = 'auto')
            hists[f][1] = [datetime.fromtimestamp(i) for i in bins]
        pickle.dump(activity, open(cls.workingPath + 'activity.pickle', 'wb'))
        pickle.dump(hists, open(cls.workingPath + 'hists.pickle', 'wb'))


    @classmethod
    def refresh_creds(cls, creds):
        path = cls.workingPath
        cls.creds = creds

        if not cls.creds or not cls.creds.valid:
            if cls.creds and cls.creds.expired and cls.creds.refresh_token:
                cls.creds.refresh(Request())
            else:
                raise "cls.creds not valid!"

            '''
            # Save the credentials for the next run
            with open(path + 'creds.pickle', 'wb') as token:
                pickle.dump(cls.creds, token)
            '''
        cls.creds.apply(cls.headers)
        return cls.creds



    @classmethod
    def dractivity_builder(cls, id):
        headers = cls.headers

        ancName = "items/" + id
        pageSize = 1000
        filter = "detail.action_detail_case: EDIT"

        #Generate random quotaUser
        quotaUser = str(uuid.uuid4())

        params = dict(ancestorName = ancName, pageSize = pageSize, 
            filter = filter, quotaUser = quotaUser)
        return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")


    @classmethod
    async def print_size(cls, files, lastModFile, FilePrintText, continuous = True):
        while True:
            totalSize = files.qsize() + len(lastModFile)
            outputString = "%s <b>%d out of %d (discovered items)</b> <br>" %(FilePrintText.text,len(lastModFile),  totalSize)

            FilePrintText.clear()

            cls.strToFile(outputString, 'streaming.txt')

            print(outputString)

            if continuous: 
                await asyncio.sleep(10)

    @classmethod
    def strToFile(cls, string, filename):
        open(cls.workingPath + filename, 'a+').write(string)
        open(filename, 'a').write(string)

consecutiveErrors = 0
def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

async def API_RESET(seconds = 30):
    global consecutiveErrors
    TestUtil.refresh_creds(TestUtil.creds)
    consecutiveErrors+=1
    seconds *=(consecutiveErrors)

    perUpdate = 10
    secInterval = math.ceil(seconds/perUpdate)

    if(consecutiveErrors > 1):
        #Too much errors, reset
        secs = random.randint(0, 50)
        TestUtil.strToFile("Waiting for GDrive... %d<br>"%(secs), 'streaming.txt')
        await asyncio.sleep(secs)
        return

    for i in range(secInterval):
        print(consecutiveErrors)
        TestUtil.strToFile("Waiting for GDrive... %d/%d <br>"%(i, secInterval), 'streaming.txt')
        await asyncio.sleep(perUpdate)

    await asyncio.sleep(random.randint(0, seconds))

async def tryGetQueue(queue: asyncio.Queue, repeatTimes:int = 5, interval:float = 3, name:str = ""):
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
            await asyncio.sleep(interval + random.randint(0, 15))
    return output

