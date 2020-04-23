import pandas as pd
import gc
import resource
from processing.throttler import Throttle
import configlog
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

tracemalloc.start(10)

logger = logging.getLogger(__name__)

class TestUtil:
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']
    fileCounter = 0
    creds = None
    headers = {}
    consecutiveErrors = 0
    pathedFiles = {}
    workingPath = None
    pickleIndex = []
    maxSize = 0
    errMsg = "BEGIN" + str(datetime.now()) + "\n"
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
        cls.errMsg += str(msg) + '\n'

    @classmethod
    @profile
    async def print_size(cls, files):
        cls.snapshot = tracemalloc.take_snapshot()
        while True:
            logger.warning('\n\nMemory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            sns = tracemalloc.take_snapshot()
            for i in sns.compare_to(cls.snapshot, 'lineno')[0:10]:
                logger.warning(i)

            cls.snapshot = sns


            gc.collect()

            totsize = files.qsize() + len(cls.pathedFiles)
            logger.info("%s\n%d/%d at %s\ndumped: %d",cls.workingPath,len(cls.pathedFiles), totsize, datetime.now().__str__(),
                    cls.fileCounter)

            logger.error(cls.errMsg)


            cls.errMsg = ""

            if(random.randint(0, 100) > 97):
                print("resetting counter")
                cls.throttle.reset()

            if(len(cls.pathedFiles)>60):
                cls.fileCounter +=1
                _filename = cls.workingPath + str(cls.fileCounter) + '.pathed'
                pickle.dump(cls.pathedFiles, open(_filename, 'wb'))
                logger.warning("dumped pathed files at %s, length %d", _filename, len(cls.pathedFiles))
                cls.pathedFiles = {}
                cls.pickleIndex.append(_filename)


            for i in range(5):
                print(f"{i*4} out of 20 till next output      ", end = "\r", flush = True)
                await asyncio.sleep(4)



    #Deprecated
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
    logger.debug("Waiting for GDrive... %d", secs)
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


