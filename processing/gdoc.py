import requests
import textwrap
import time
from pprint import pformat
import random
import aiohttp
import asyncio
import ujson as json
import logging

from multiprocessing import Pipe, Process, Event


from types import SimpleNamespace
from collections import namedtuple

logger = logging.getLogger(__name__)

base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'
url = 'https://www.googleapis.com/drive/v3/files/{}/revisions'

timeout = aiohttp.ClientTimeout(total=3)


Closure = namedtuple("Closure", ['parent', 'child', 'depth'])

class Operation():
    def __init__(self, date, content):
        self.date = date
        self.content = content

    def __repr__(self):
        return f'Date: {self.date}, content: {self.content}'

def round_time(d, round_by = 120):
    return round_by * round(d / round_by)


gd_condensed = namedtuple('gd_condensed', ['name', 'path', 'operations', 'closure', 'fileId'])


class GDoc():

    __slots__ = ['path', 'name', 'last_revision_id', 'fileId', 'session', 'headers', 'operations', 'closure', 'done']

    sem = asyncio.Semaphore(value = 9)

    def return_condensed(self):
        if not self.operations:
            logger.critical("Operations not found but still returning condensed!! %s %s %s", self.name, self.fileId, self.operations)
        return gd_condensed(self.name, self.path, self.operations, self.closure, self.fileId)


    def __init__(self):
        self.done = False

    async def async_init(self, name,  fileId, session, headers, path):
        self.operations = []
        self.closure = []
        self.name = name
        self.last_revision_id = 1

        logger.debug("async init called")
        self.fileId = fileId
        self.path = path

        self.session = session
        self.headers = headers
        self.last_revision_id = 1

        await self.get_last_revision()

        logger.debug("starting googledoc async_init for %s", fileId)

        retries = 1

        while retries:
            retries -= 1

            parent_conn, child_conn = Pipe()

            p = Process(target = self._download_details, args = (child_conn,))

            async with GDoc.sem:

                p.start()

                logger.debug("started process for %s", fileId[0:5])
                await asyncio.sleep(5)

                counter = 0
                while not parent_conn.poll(0.01) and counter < 5:
                    counter +=1
                    logger.debug("sleeping from poll, waiting for %s, %d", fileId[0:5], counter)
                    await asyncio.sleep(random.uniform(6 * counter, 10 * counter))

                logger.debug("received goahead to receive %s", fileId[0:5])

                if parent_conn.poll(0.01):
                    self.operations = parent_conn.recv()
                    if self.operations == []:
                        logger.warning("No content received for: %s, %s.", self.fileId, self.name)
                    parent_conn.send(f'success {fileId[0:5]}')
                    p.terminate()
                    p.join(0.01)
                    retries = 0
                else:
                    p.terminate()
                    p.join(0.01)
                parent_conn.close()

        self.compute_closure()

        if self.operations:
            self.done = True
        else:
            self.done = False
        logger.info("Done computing gdoc for %s %s", self.name, self.fileId)



    async def get_last_revision(self, retry = False):

        try:
            async with self.session.get(url=url.format(self.fileId), 
                    headers=self.headers, timeout = timeout) as response:
                code = response.status
                if code != 200:
                    if retry:
                        return -1
                    logger.info("can't get last revision, sleeping 7")
                    await asyncio.sleep(random.uniform(10, 20))
                    await self.get_last_revision(retry = True)
                else:
                    rev = await response.text()
                    rev = json.loads(rev)
                    self.last_revision_id = rev["revisions"][-1]["id"]
                    logger.debug("last revision id %s", self.last_revision_id)
                    return 0
        except:
            logger.debug("cannot get last revision id")

    def compute_closure(self):

        assert self.path[-1][0] == self.fileId, f"{self.path[-1]};{self.fileId}"

        for c, i in enumerate(self.path):
            child = self.path[-1]
            parent = i
            self.closure.append(Closure(parent = parent, child = child, depth = len(self.path) -c -1))


        return self.closure



    def _download_details(self,  pipe):

        logger.info("received job for %s",self.fileId)

        revision_details = dict(changelog = [])

        #Retries
        for i in range(1, 3):
            url = base_url.format(file_id=self.fileId, end=self.last_revision_id)
            response = SimpleNamespace(text = "Blank Filler. This will show when response is undefined")
            try:
                response = requests.get(url = url, headers = self.headers, timeout = 10)
                assert response.status_code == 200
            except:
                logger.debug("%s unable, sleeping up to %d", self.fileId[0:5], 20*i)
                time.sleep(random.uniform(5, 20*i))
                continue
            text = response.text
            revision_details = json.loads(text[5:])
            break

        tot_operations = []
        for count,x in enumerate(revision_details['changelog']):

            if x[0]['ty'] not in {'is', 'ds'}:
                continue

            if x[0]['ty'] == 'is':
                content = [len(x[0]['s']), 0]
            elif x[0]['ty'] == 'ds':
                content = [0, x[0]['ei'] - x[0]['si'] + 1]

            cur_op = Operation(date = x[1]/1e3, content = content)
            tot_operations.append(cur_op)


        #Condense all operations into minute-operations
        operation_condensed = {}
        for o in tot_operations:
            key = round_time(o.date)
            if key not in operation_condensed:
                operation_condensed[key] = o
            else:
                operation_condensed[key].content[0] += o.content[0]
                operation_condensed[key].content[1] += o.content[1]

        operations = list(operation_condensed.values())

        pipe.send(operations)
        time.sleep(10)

        counter = 1
        while not pipe.poll(0.01):

            logger.debug("resending for %s, counter %d", self.fileId[0:5], counter)
            pipe.send(operations)
            counter +=1

            time.sleep(random.uniform(12 * counter, 15 * counter))

            if counter > 5:
                logger.debug("waited too long, not resending")
                pipe.send(operations)
                pipe.close()
                return

        logger.debug("pipe received: %s correct: %s after %d", pipe.recv(), self.fileId[0:5], counter)
        pipe.close()

        return

    def __repr__(self):
        s = "GDoc Object\n\t%s\n\t%s"%(pformat(self.operations), pformat(self.closure))
        return s



