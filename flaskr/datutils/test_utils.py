import pandas as pd
from flaskr.throttler import Throttle
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
    errMsg = "BEGIN" + str(datetime.now()) + "<br> \n\n"
    throttle = None

    @classmethod
    def formatData(cls, fileName = 'collapsedFiles'):
        rdata = pickle.load(open(cls.workingPath + fileName + '.pickle', 'rb'))

        ind = pd.MultiIndex.from_tuples(rdata.keys())
        data = pd.DataFrame(rdata.values(), index = ind, columns = ["Type"])

        sumDates=data.reset_index(level = 0, drop = True)
        pickle.dump(data, open(cls.workingPath + fileName + "_p.pickle", 'wb'))


    @classmethod
    def activity_gen(cls):
        data = pickle.load(open(cls.workingPath + 'collapsedFiles_p.pickle', 'rb'))
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
    def errors(cls, msg):
        cls.errMsg += str(msg) + '<br> \n'

    @classmethod
    async def print_size(cls, files, lastModFile, FilePrintText):
        while True:
            totalSize = files.qsize() + len(lastModFile)
            outputString = "%s <b>%d out of %d (discovered items)</b> <br>" %(FilePrintText.text,len(lastModFile),  totalSize)

            FilePrintText.clear()

            cls.strToFile(outputString, 'streaming.txt')
            cls.strToFile(cls.errMsg, 'errors.txt')

            cls.errMsg = "CLEARED " + datetime.now() + "\n"

            print(outputString)
            print('counter: ', cls.throttle.gcount(), '   rpm: ', cls.throttle.rpm)

            if(random.randint(0, 100) > 95):
                print("resetting counter")
                cls.throttle.reset()
            await asyncio.sleep(2)


    @classmethod
    def strToFile(cls, string, filename):
        open(cls.workingPath + filename, 'a+').write(string)
        open(filename, 'a+').write(string)

def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

async def API_RESET(seconds = 6, throttle = None, decrease = False):

    if throttle and decrease:
        throttle.decrease()
    secs = random.randint(0, seconds)
    TestUtil.strToFile("Waiting for GDrive... %d<br>"%(secs), 'streaming.txt')
    await asyncio.sleep(secs)
    return

async def tryGetQueue(queue: asyncio.Queue, repeatTimes:int = 5, interval:float = 10, name:str = ""):
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

