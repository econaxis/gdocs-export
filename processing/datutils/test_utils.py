import collections
import os
import ujson as json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import sys
#from memory_profiler import profile
import gc
#import resource
import tracemalloc
import random
from datetime import datetime
import asyncio
import time
import pickle
from google.auth.transport.requests import Request
import logging

if "FLASKDBG" in os.environ:
    print("flask debug in os environ")
    SERVER_ADDR = "127.0.0.1"
else:
    SERVER_ADDR = 'sql'
"""
if (random.random() < 0.0):
    os.environ["PROFILE"] = "true"
"""

Info = collections.namedtuple('Info', ['userid', 'files', 'extra'],
                              defaults=('default' + str(datetime.now()), [],
                                        'task'))
logger = logging.getLogger(__name__)


class TestUtil:

    totsize = 0
    cur_count = 0
    fileCounter = 0
    creds = None
    headers = {}
    files = []
    idmapper = {}
    sql_server_active = False
    MAX_FILES = 30
    userid = None
    workingPath = None
    processedcount = 0
    drive = None

    #Used for debugging purposes for measuring rate
    _prev_count = (0, time.time())

    info = Info()

    @classmethod
    def refresh_creds(cls, creds):
        cls.workingPath
        cls.creds = creds

        if not cls.creds or not cls.creds.valid:
            if cls.creds and cls.creds.expired and cls.creds.refresh_token:
                cls.creds.refresh(Request())
            else:
                raise "cls.creds not valid!"

        cls.creds.apply(cls.headers)
        cls.drive = build('drive', 'v3', credentials = cls.creds)
        return cls.creds

    @classmethod
    def dractivity_builder(cls, id):
        headers = cls.headers

        ancName = "items/" + id
        pageSize = 1000
        filter = "detail.action_detail_case: EDIT"

        params = dict(ancestorName=ancName, pageSize=pageSize, filter=filter)
        return dict(
            params=params,
            headers=headers,
            url="https://driveactivity.googleapis.com/v2/activity:query")

    #@profile
    @classmethod
    async def print_size(cls, files, endEvent):
        cls.starttime = time.time()

        if ("PROFILE" in os.environ):
            tracemalloc.start()
            cls.snapshot = tracemalloc.take_snapshot()

        while not endEvent.is_set():
            gc.collect()

#            logger.warning('\n\n%sMemory usage: %s (kb)%s%f mins since start',
#                           '-' * 15,
#                           resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
#                           '-' * 15, (time.time() - cls.starttime) / 60)

            if ("PROFILE" in os.environ):
                sns = tracemalloc.take_snapshot()
                for i in sns.compare_to(cls.snapshot, 'lineno')[0:5]:
                    logger.info(i)
                logger.info('%s', '-' * 60)
                for i in sns.statistics('lineno')[0:5]:
                    logger.info(i)
                cls.snapshot = sns

            cls.totsize = files.qsize() + len(cls.files) + cls.processedcount

            cls.cur_count = len(cls.files) + cls.processedcount

            rate = (cls.cur_count - cls._prev_count[0]) / (time.time() -
                                                       cls._prev_count[1]) * 60

            logger.info("%d/%d discovered items \ndump count: %d; rate is %d per min", \
                    cls.cur_count, cls.totsize ,cls.fileCounter, rate)

            cls._prev_count = (cls.cur_count, time.time())

            _sleep_time = 10
            check_times = 2

            for _ in range(check_times):
                await asyncio.sleep(_sleep_time / check_times)
                if cls.cur_count > cls.MAX_FILES:
                    #We have exceeded the max file limit. We set the endEvent so hopefully all the other workers will
                    #end too
                    logger.info("cur_count %d is larger than max_files",
                                cls.cur_count)
                    endEvent.set()
                    break

        logger.warning("print task return")

    @classmethod
    async def dump_files(cls, return_thread=False, upload=False):

        if not upload:
            return True

        condensed_files = [x.return_condensed() for x in cls.files]

        info_packet = Info(userid=cls.userid,
                           files=condensed_files,
                           extra='upload' if upload else None)

        success = False

        while not (await cls.send_socket(info_packet)):
            logger.info("send socket not succeeded, sleeping 60")

            #Blocks the event loop
            time.sleep(random.randint(40, 70))

        if success:
            cls.fileCounter += 1
            cls.processedcount += len(cls.files)
            cls.files = []
        else:
            logger.warning("dump_files socket send denied")

        return success

    @classmethod
    async def test_server(cls, info_packet):
        logger.info("connect working")

        logger.info("server addr: %s", SERVER_ADDR)
        r, w = await asyncio.open_connection(SERVER_ADDR, 8888)

        message = b"request"

        await adv_write(w, message)

        m = await adv_read(r)
        logger.info("received: %s", m)

        if m != b'go':
            return False

        if m == b'go':
            await adv_write(w, info_packet, to_pickle=True)
        w.close()
        return True

    @classmethod
    async def send_socket(cls, info_packet):
        cls.info = info_packet._replace(files=cls.info.files +
                                        info_packet.files)

        if info_packet.extra == 'upload':
            logger.info("Uploading info")
            pickle.dump(cls.info, open('info', 'wb'))
        return True


    @classmethod
    async def handleResponse(cls, response, fileTuple=None, queue=None):
        try:
            rev = await response.text()
            rev = json.loads(rev)
            assert response.status == 200, "Response not 200"
            return rev
        except:
            sys.exc_info()[0]
            rev = await response.text()
            logger.debug("response error %s", rev)

            if (fileTuple and queue and fileTuple[-1] < 2):
                fileTuple = list(fileTuple)
                fileTuple[-1] += 1
                await queue.put(fileTuple)

            return -1


def dr2_urlbuilder(id: str):
    return "https://www.googleapis.com/drive/v2/files/" + id + "/revisions"


async def API_RESET(seconds=6, throttle=None, decrease=False):

    if throttle and decrease:
        await throttle.decrease()
    secs = random.randint(0, seconds)
    logger.debug("Waiting for GDrive... %d", secs)
    await asyncio.sleep(secs)
    return


async def tryGetQueue(queue: asyncio.Queue,
                      repeatTimes: int = 2,
                      interval: float = 3,
                      name: str = ""):
    output = None
    timesWaited = 0
    while (output == None):
        try:
            timesWaited += 1
            output = queue.get_nowait()
        except:
            if (timesWaited > repeatTimes):
                return -1
            logger.info(name + "waiting %d %d", timesWaited, repeatTimes)
            await asyncio.sleep(random.uniform(0.8 * interval, 1.4 * interval))
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

    if to_pickle:
        return pickle.loads(data)
    else:
        return data


async def adv_write(writer, data, to_pickle=False):
    import struct

    if to_pickle:
        data = pickle.dumps(data)

    header = struct.pack('!Q?', len(data), to_pickle)
    writer.write(header)
    writer.write(data)
    await writer.drain()

    return
