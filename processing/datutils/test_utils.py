import collections
import os
import ujson as json
import random
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

queue_wait_time = 0

class TestUtil:

    totsize = 0
    cur_count = 0
    fileCounter = 0
    creds = None
    headers = {}
    files = []
    MAX_FILES = int(os.environ.get("MAX_FILES", 10))
    userid = None
    workingPath = None
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
        cls.files_queue = files

        while not endEvent.is_set():
            cls.gcollect()
            
            cls.calc_totsize()

            diff_time = time.time() - cls._prev_count[1]
            rate = (cls.cur_count - cls._prev_count[0]) / (diff_time) * 60
            if diff_time > 20:
                cls._prev_count = (cls.cur_count, time.time())


            logger.info("%d/%d discovered items \ndump count: %d; rate is %d per min\n total queue wait time %d", \
                    cls.cur_count, cls.totsize ,cls.fileCounter, rate, queue_wait_time)


            _sleep_time = 5
            check_times = 10

            for _ in range(check_times):
                await asyncio.sleep(_sleep_time / check_times)
                if cls.cur_count > cls.MAX_FILES:
                    logger.info("cur_count %d is larger than max_files", cls.cur_count)
                    endEvent.set()
                    break
        logger.warning("print task return")
    @classmethod
    def calc_totsize(cls):
        cls.cur_count = len(cls.files)
        cls.totsize = cls.files_queue.qsize() + cls.cur_count

        return cls.totsize


    @classmethod
    def dump_files(cls):
        condensed_files = [x.return_condensed() for x in cls.files]

        info_packet = Info(userid=cls.userid,
                           files=condensed_files,
                           extra='upload')

        return info_packet

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



async def tryGetQueue(queue,
                      repeatTimes: int = 2,
                      interval: float = 3,
                      name: str = "",
                      endEvent = None):
    output = None
    timesWaited = 0
    while (output == None):
        if endEvent and endEvent.is_set():
            return -1
        try:
            output = queue.get_nowait()
        except asyncio.queues.QueueEmpty:
            timesWaited += 1
            if (timesWaited > repeatTimes):
                return -1
            logger.info(name + "waiting %d %d", timesWaited, repeatTimes)

            if name == "getRevision":
                queue_wait_time += timesWaited * 3
                await asyncio.sleep(timesWaited * 3)
    return output


#  async def adv_read(reader):
#      import struct
#      header = await reader.readexactly(9)
#      header = struct.unpack('!Q?', header)
#  
#      to_pickle = header[1]
#      length = header[0]
#  
#      data = []
#  
#      per_read = 5000
#  
#      while length > 0:
#          try:
#              data.append(await reader.readexactly(min(length, per_read)))
#          except asyncio.IncompleteReadError as e:
#              data.append(e.partial)
#              length -= len(e.partial)
#          else:
#              length -= min(length, per_read)
#  
#      data = b"".join(data)
#  
#      if to_pickle:
#          return pickle.loads(data)
#      else:
#          return data
#  
#  
#  async def adv_write(writer, data, to_pickle=False):
#      import struct
#  
#      if to_pickle:
#          data = pickle.dumps(data)
#  
#      header = struct.pack('!Q?', len(data), to_pickle)
#      writer.write(header)
#      writer.write(data)
#      await writer.drain()
#  
#      return
