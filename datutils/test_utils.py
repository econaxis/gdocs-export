import pandas as pd
import numpy as np
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
    pydocPath = None
    creds = None
    headers = {}
    consecutiveErrors = 0
    workingPath = None

    @classmethod
    def formatData(cls, fileName = 'collapsedFiles'):
        rdata = pickle.load(open(cls.workingPath + fileName + '.pickle', 'rb'))

        ind = pd.MultiIndex.from_tuples(rdata.keys())
        data = pd.DataFrame(rdata.values(), index = ind, columns = ["Type"])

        sumDates=data.reset_index(levels = 0, drop = True)
        data.to_pickle(cls.workingPath + fileName + "_p.picke")


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
    def creds_from_pickle(cls):
        path = cls.workingPath

        with open(path+'creds.pickle', 'rb') as cr:
            cls.creds = pickle.load(cr)

        if not cls.creds or not cls.creds.valid:
            if cls.creds and cls.creds.expired and cls.creds.refresh_token:
                cls.creds.refresh(Request())
            else:
                raise "cls.creds not valid!"
            # Save the credentials for the next run
            with open(path + 'token.pickle', 'wb') as token:
                pickle.dump(cls.creds, token)

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
    async def print_size(cls, folder, file):
        while True:
            outputString = "FLDR SZ: %d FILE SZ: %d\n" %(folder.qsize(), file.qsize())

            streamingFile = open(cls.pydocPath + "streaming.txt", 'a')
            streamingFile.write(outputString)
            print(outputString)
            await asyncio.sleep(3)



consecutiveErrors = 0
def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

def API_RESET(seconds = 10):
    global consecutiveErrors
    consecutiveErrors+=1
    seconds *=(consecutiveErrors)
    for i in range(math.ceil(seconds/10)):
        print(consecutiveErrors)
        print("%d/%d"%(i, math.ceil(seconds/10)))
        time.sleep(10)

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

