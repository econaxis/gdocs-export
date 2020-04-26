import pandas as pd
from multiprocessing import Process
import os
import ujson as json
import sys
#from memory_profiler import profile
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


if (random.random() < 0.2 ):
    os.environ["PROFILE"] = "true"


logger = logging.getLogger(__name__)

class TestUtil:


    fileCounter = 0
    creds = None
    headers = {}
    pathedFiles = {}
    workingPath = None
    pickleIndex = []
    processedcount = 0


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
    async def print_size(cls, files, endEvent):
        cls.starttime = time.time()
        if ("PROFILE" in os.environ):
            tracemalloc.start()
            cls.snapshot = tracemalloc.take_snapshot()
        while not endEvent.is_set():
            logger.warning('\n\n%sMemory usage: %s (kb)%s%d mins since start','-'*15,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, '-'*15,
                    (time.time() - cls.starttime)/60)

            if("PROFILE" in os.environ):
                sns = tracemalloc.take_snapshot()
                for i in sns.compare_to(cls.snapshot, 'lineno')[0:5]:
                    logger.info(i)

                logger.info('%s','-'*60)

                for i in sns.statistics('lineno')[0:5]:
                    logger.info(i)

                cls.snapshot = sns

            gc.collect()

            totsize = files.qsize() + len(cls.pathedFiles) + cls.processedcount


            logger.info("%s\n%d/%d discovered items at %s\ndump count: %d", \
                    cls.workingPath,len(cls.pathedFiles) + cls.processedcount, totsize, datetime.now().__str__() \
                    ,cls.fileCounter)

            #Temp var for thread
            p = None

            if len(cls.pathedFiles)>20:
                cls.dump_files()

                p = configlog.sendmail(return_thread = True)


            _sleep_time = 30
            for i in range(3):
                #print(f"{i*_sleep_time/3} out of {_sleep_time} till next output      ", end = "\r", flush = True)
                await asyncio.sleep(_sleep_time/3)

            if p:
                p.join()

    @classmethod
    def dump_files(cls):

        histo = {}
        
        for i in cls.pathedFiles:
            #list of datetime timestamps for each file
            histo[i] = [None, None]
            histo[i] = cls.compute_hist(cls.pathedFiles[i])

        length = len(cls.pathedFiles)
        cls.processedcount +=length
        cls.fileCounter +=1

        _filename = cls.workingPath + str(cls.fileCounter) + '.pathed'

        p = Process(target = mp_dump, args = (histo, _filename,))
        p.start();



        #Dumped histo


        logger.info("histed files at %s, length %d", _filename, length)

        cls.pathedFiles = {}

        cls.pickleIndex.append(_filename)

        p.join()

    @classmethod
    def compute_hist(cls, data, bin_method = 'fd'):

        _ret = np.histogram(data, bins = 'fd')

        #Return list of values, bins
        return [_ret[0].tolist(), _ret[1].tolist()]



    @classmethod
    async def handleResponse(cls, response, fileTuple = None, queue = None):
        try:
            rev = await response.text()
            rev = json.loads(rev)
            assert response.status == 200, "Response not 200"
            return rev
        except:
            e = sys.exc_info()[0]
            rev = await response.text()
            logger.log(5, rev)



            if(fileTuple and queue and fileTuple[-1] < 2):
                fileTuple = list(fileTuple)
                fileTuple[-1] += 1
                await queue.put(fileTuple)

            return -1


    '''
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
    '''


def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"

async def API_RESET(seconds = 6, throttle = None, decrease = False):

    if throttle and decrease:
        await throttle.decrease()
    secs = random.randint(0, seconds)
    logger.debug("Waiting for GDrive... %d", secs)
    await asyncio.sleep(secs)
    return

async def tryGetQueue(queue: asyncio.Queue, repeatTimes:int = 5, interval:float = 3.5, name:str = ""):
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
            await asyncio.sleep(interval + random.randint(0, 5))
    return output



def mp_dump(info, filename):
    pickle.dump(info, open(filename, 'wb'))
