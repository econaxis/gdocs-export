import collections
import os
import ujson as json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from configlog import tracer
from datetime import datetime
import asyncio
import time
import pickle
import logging

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
    MAX_FILES = 40
    userid = None
    workingPath = None
    processedcount = 0
    drive = None

    #Used for debugging purposes for measuring rate
    _prev_count = (0, time.time())

    info = Info()


    gc_last_time = time.time()

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

    @classmethod
    def gcollect(cls):
        if time.time() - cls.gc_last_time < 30:
            return
        cls.gc_last_time = time.time()

        import gc
        gc.collect()



    tracer.prof("print_size")
    @classmethod
    async def print_size(cls, files, endEvent):
        while not endEvent.is_set():
            cls.gcollect()

            cls.cur_count = len(cls.files) + cls.processedcount
            cls.totsize = files.qsize() + cls.cur_count

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
                    logger.info("cur_count %d is larger than max_files", cls.cur_count)
                    endEvent.set()
                    break

        logger.warning("print task return")

    @classmethod
    async def dump_files(cls):
        condensed_files = [x.return_condensed() for x in cls.files]

        info_packet = Info(userid=cls.userid,
                           files=condensed_files,
                           extra='upload')

        cls.info = info_packet



    @classmethod
    async def handleResponse(cls, response, fileTuple=None, queue=None):
        try:
            rev = await response.text()
            rev = json.loads(rev)
            assert response.status == 200, "Response not 200"
            return rev
        except:
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
