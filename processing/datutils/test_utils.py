import collections
from multiprocessing import Process
from pprint import pformat
import os
import ujson as json
import sys
#from memory_profiler import profile
import gc
import resource
import configlog
import tracemalloc
import random
from datetime import datetime
import google.oauth2.credentials
import asyncio
import time
import pickle
from google.auth.transport.requests import Request
import logging



if (random.random() < 0 ):
    os.environ["PROFILE"] = "true"


Info = collections.namedtuple('Info', ['userid', 'files', 'extra'],
        defaults = ('default' + str(datetime.now()), [], None))
logger = logging.getLogger(__name__)

class TestUtil:


    ROUND_BY = 500
    fileCounter = 0
    creds = None
    headers = {}
    files = []
    idmapper = {}
    userid = None
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

        params = dict(ancestorName = ancName, pageSize = pageSize,
            filter = filter)
        return dict(params = params, headers = headers, url = "https://driveactivity.googleapis.com/v2/activity:query")


    @classmethod
    async def print_size(cls, files, endEvent):
        cls.starttime = time.time()
        if ("PROFILE" in os.environ):
            tracemalloc.start()
            cls.snapshot = tracemalloc.take_snapshot()

        start_time = time.time()
        p = None
        while not endEvent.is_set():

            if random.random() < 0.3:
                p = configlog.sendmail(msg = str(datetime.now()), return_thread = True)

            gc.collect()

            logger.warning('\n\n%sMemory usage: %s (kb)%s%d mins since start'
                    ,'-'*15,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, '-'*15,
                    (time.time() - cls.starttime)/60)


            if("PROFILE" in os.environ):
                sns = tracemalloc.take_snapshot()
                for i in sns.compare_to(cls.snapshot, 'lineno')[0:5]:
                    logger.info(i)

                logger.info('%s','-'*60)

                for i in sns.statistics('lineno')[0:5]:
                    logger.info(i)

                cls.snapshot = sns


            totsize = files.qsize() + len(cls.files) + cls.processedcount


            logger.info("%s\n%d/%d discovered items at %s\ndump count: %d", \
                    cls.workingPath,len(cls.files) + cls.processedcount, totsize, datetime.now().__str__() \
                    ,cls.fileCounter)

            #Temp var for thread

            _sleep_time = 16
            interval = 2

            df_t = []

            for i in range(interval):
                if endEvent.is_set():
                    break
                if len(cls.files)>10:
                    code = await cls.dump_files()
                    while not code:
                        logger.warning ("SQL Socket Send denied, retrying")
                        time.sleep(30)
                        code = await cls.dump_files()

                await asyncio.sleep(_sleep_time / interval)

            a0 = time.time()
            logger.debug("file save time: %f", time.time() - a0)

            logger.debug("event loop health: %d, intended: %d", time.time() - start_time, _sleep_time)
            start_time = time.time()

            if p:
                logger.debug("awaiting email task join")
                p.join(timeout = 0.01)
                logger.debug("done awaiting task join")

        logger.warning("print task return")


    @classmethod
    async def dump_files(cls, return_thread = False):

        condensed_files = [x.return_condensed() for x in cls.files]
        info_packet = Info(userid = cls.userid, files = condensed_files)


        success = await cls.send_socket(info_packet)

        while not success:
            logger.info("send socket not succeeded")
            time.sleep(40)
            success = await cls.send_socket(info_packet)

        if success:
            cls.fileCounter += 1
            cls.processedcount += len(cls.files)
            cls.files = []
        else:
            logger.warning("dump_files socket send denied")

        return success

    @classmethod
    async def send_socket(cls, info_packet):

        s = pformat(info_packet)
        _step = 5000
        for i in range(0, len(s), _step):
            logger.debug("\n%s\n", s[i:i+_step])



        logger.info("connect working")
        r, w = await asyncio.open_connection('sql_serv', 8888)

        message= b"request"


        await adv_write(w, message)

        m = await adv_read(r)
        logger.info("received: %s", m)

        if m != b'go':
            return False


        if m == b'go':
            await adv_write(w, info_packet, to_pickle = True)

        w.close()
        return True

    @classmethod
    def _round_func(cls, x, round_by = None):

        if round_by == None:
            round_by = cls.ROUND_BY
        return round_by * round(x/round_by)

    """

    @classmethod
    def compute_hist(cls, data, bin_method = 'fd'):
        #Data is a list of timestamps

        values = []
        bins = []
        bin_width = cls.ROUND_BY
        isTime = []
        data = sorted(data, key = cls._round_func)
        for key, group in groupby(data, cls._round_func):
            bins.append(key)
            values.append(len(list(group)))
            isTime.append(False)


        times = []
        for x in data:
            dt = datetime.fromtimestamp(x).replace(year = 2, month = 1, day =1).timestamp()

            #Five second precision
            times.append(cls._round_func(dt, round_by = 5))

        for key, group in groupby(times):
            bins.append(key)
            values.append(len(list(group)))
            isTime.append(True)

        #Return list of values, bins
        return [values, bins, isTime, bin_width]

    """

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
            logger.info(name + "waiting %d %d", timesWaited, repeatTimes)
            await asyncio.sleep(interval + random.randint(0, 5))
    return output



def mp_dump(info, filename):
    pickle.dump(info, open(filename, 'wb'))



async def adv_read(reader):
    import struct
    header = await reader.readexactly(9)
    header = struct.unpack('!Q?', header)

    to_pickle = header[1]
    length = header[0]

    data = []

    _length = length

    per_read = 5000

    while length > 0:
        try:
            data.append(await reader.readexactly(min(length, per_read)))
        except asyncio.IncompleteReadError as e:
            data.append(e.partial)
            length -= len(e.partial)
        else:
            length -= min(length, per_read)

    data = b"".join(data)

    print("length of read: ", len(data), _length)

    if to_pickle:
        return pickle.loads(data)
    else:
        return data

async def adv_write(writer, data, to_pickle = False):
    import struct

    if to_pickle:
        data = pickle.dumps(data)

    logger.info("length of write: %d", len(data))

    header = struct.pack('!Q?', len(data), to_pickle)

    logger.info(header)

    writer.write(header)
    writer.write(data)
    await writer.drain()

    return

