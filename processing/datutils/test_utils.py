import pandas as pd
from guppy import hpy
from processing.throttler import Throttle
import tracemalloc
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
import logging

tracemalloc.start(250)

logger = logging.getLogger(__name__)

class TestUtil:
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']
    fileCounter = 0
    creds = None
    headers = {}
    consecutiveErrors = 0
    workingPath = None
    pickleIndex = []
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
        #deprecated
        quotaUser = str(uuid.uuid4())

        params = dict(ancestorName = ancName, pageSize = pageSize,
            filter = filter, quotaUser = quotaUser)
        return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")

    @classmethod 
    def errors(cls, msg):
        cls.errMsg += str(msg) + '<br> \n'

    @classmethod
    async def print_size(cls, FilePrintText, pathedFiles, files):
        cls.snapshot = tracemalloc.take_snapshot()
        hp = hpy()
        while True:
            print(hp.heap().__str__())
            snapshot = tracemalloc.take_snapshot().compare_to(cls.snapshot, 'lineno')
            for st in snapshot[0:10]:
                print(st)

            import resource
            logger.warning( 'Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

            cls.snapshot = tracemalloc.take_snapshot()
            if(len(pathedFiles)>5):
                cls.fileCounter +=1
                _filename = cls.workingPath + str(cls.fileCounter) + '.pathed'
                logger.info("dumped pathed files at %s", _filename)
                pickle.dump(pathedFiles, open(_filename, 'wb'))
                pathedFiles = {}
                cls.pickleIndex.append(_filename)

            totsize = files.qsize() + len(pathedFiles)
            outputString = "\n\nuser: %s\n%s\n%d/%d (discovered items)\n%s\n" %(cls.workingPath,FilePrintText.text,len(pathedFiles), totsize,
                    datetime.now().__str__())

            outputString += "counter: %f rpm: %f\n"%(cls.throttle.gcount(), cls.throttle.rpm)
            FilePrintText.clear()

            logger.info(outputString)
            if(cls.errMsg != ""):
                logger.error(cls.errMsg)


            cls.errMsg = ""

            if(random.randint(0, 100) > 97):
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
        await throttle.decrease()
    secs = random.randint(0, seconds)
    TestUtil.strToFile("Waiting for GDrive... %d<br>"%(secs), 'streaming.txt')
    await asyncio.sleep(secs)
    return

async def tryGetQueue(queue: asyncio.Queue, repeatTimes:int = 2, interval:float = 2, name:str = ""):
    output = None
    timesWaited = 0
    while(output==None):
        try:
            timesWaited+=1
            output = queue.get_nowait()
        except:
            if(timesWaited>repeatTimes):
                return -1
            logger.debug(name + "waiting %d %d", timesWaited, repeatTimes)
            await asyncio.sleep(interval + random.randint(0, 15))
    return output


