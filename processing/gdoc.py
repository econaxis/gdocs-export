import certifi
import time
from io import BytesIO
from pprint import pformat
from configlog import tracer
import random
import aiohttp
import asyncio
import ujson as json
import logging


from collections import namedtuple


from threading import Lock

logger = logging.getLogger(__name__)

base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'
url = 'https://www.googleapis.com/drive/v3/files/{}/revisions'

timeout = aiohttp.ClientTimeout(total=15)

Closure = namedtuple("Closure", ['parent', 'child', 'depth'])

threads = 3


try:
    import pycurl
    lock = [Lock() for i in range(threads)]
    c = [pycurl.Curl() for i in range(threads)]
except ImportError as e:
    # TODO: use requests as backup when pycurl is unavailable e.g. in repl.it
    raise e
    # import requests


#@profile
def download(url, headers):
    logger.debug("thread submitted %s %s", url, headers)
    for _ in range(5):
        for idx, l in enumerate(lock):
            if(l.acquire(blocking = False)):
                try:
                    it = zip(headers.keys(), headers.values())
                    curl_headers = [f"{k}: {v}" for k, v in it]
                    buffer = BytesIO()
                    c[idx].setopt(c[idx].CAINFO, certifi.where())
                    c[idx].setopt(c[idx].URL,url)
                    c[idx].setopt(c[idx].WRITEDATA, buffer)
                    c[idx].setopt(pycurl.HTTPHEADER, curl_headers)
                    c[idx].perform()
                    res = buffer.getvalue().decode('iso-8859-1')
                except:
                    logger.exception("")
                    return False
                finally:
                    l.release()
                    return res
        logger.info("All curl instances in use")
        time.sleep(5)


    return ""



class Closure(namedtuple("Closure", ['parent', 'child', 'depth'])):
    def __repr__(self):
        return 'p: {} c: {}\n'.format(self.parent[1], self.child[1])


class Operation():

    def __init__(self, date, content):
        self.date = date
        self.content = content

    def __repr__(self):
        return f'Date: {self.date}, content: {self.content}'


def round_time(d, round_by=30):
    return round_by * round(d / round_by)


gd_condensed = namedtuple('gd_condensed',
                  ['name', 'path', 'operations', 'closure', 'fileId'])


from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers = threads)

class GDoc():

    __slots__ = [
        'path', 'name', 'last_revision_id', 'fileId', 'session', 'headers',
        'operations', 'closure', 'done'
    ]

    sem = asyncio.Semaphore(value=30)

    def return_condensed(self):
        if not self.operations:
            logger.debug(
                "Operations not found but still returning condensed!! %s %s %s",
                self.name, self.fileId, self.operations)
        return gd_condensed(self.name, self.path, self.operations, self.closure,
                            self.fileId)

    def __init__(self):
        self.done = False

    async def file_async_init(self, file, session, headers):
        return await self.async_init(file.name, file.id, session, headers, file.path, file.last_revision_id)

    #@profile
    async def async_init(self, name, fileId, session, headers, path, last_revision_id):
        with tracer.span("gdoc"):
            self.operations = []
            self.closure = []
            self.name = name
            self.last_revision_id = 1

            logger.debug("async init called")
            self.fileId = fileId
            self.path = path

            self.session = session
            self.headers = headers
            self.headers["pageSize"] = "1000"
            self.headers["fields"] = "revisions(id)"
            self.last_revision_id = last_revision_id



            logger.debug("starting googledoc async_init for %s", fileId)

            with tracer.span("download_details"):
                self.operations = await self._download_details();


            self.compute_closure()

            if self.operations:
                self.done = True
            else:
                self.done = False
            logger.debug("Done computing gdoc for %s %s", self.name, self.fileId)

    def compute_closure(self):

        logger.debug("path: %s", list(zip(*self.path))[1])

        assert self.path[-1][0] == self.fileId, f"Last path is not fileId? {self.path[-1]};{self.fileId}"

        for c, i in enumerate(self.path):
            for c1, i1 in enumerate(self.path[c:]):
                self.closure.append(Closure(parent=i, child=i1, depth=c1))

        return self.closure

    #@profile
    async def _download_details(self):

        logger.debug("received job for %s", self.fileId)

        revision_details = dict(changelog=[])
        url = base_url.format(file_id=self.fileId,
                  end=self.last_revision_id)

        ev = asyncio.Event()

        def notify(fds):
            ev.set()

         
        revision_details = None
        for _ in range(3):
            job_handle = executor.submit(download, url, self.headers)
            job_handle.add_done_callback(notify)
            await ev.wait()
            if job_handle.result():
                revision_details = json.loads(job_handle.result()[5:])

        if not revision_details:
            return



        tot_operations = []
        content = [0, 0]

        for x in revision_details['changelog']:
            try:
                if x[0]['ty'] not in {'is', 'ds', 'mlti'}:
                    continue
            except:
                pass

            if x[0]['ty'] == 'mlti':
                for i in x[0]['mts']:
                    revision_details['changelog'].append([i, x[1]])
                continue

            if x[0]['ty'] == 'is':
                content = [len(x[0]['s']), 0]
            elif x[0]['ty'] == 'ds':
                content = [0, x[0]['ei'] - x[0]['si'] + 1]

            cur_op = Operation(date=x[1] / 1e3, content=content)
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

        return operations


    def __repr__(self):
        s = "GDoc Object\n\t%s\n\t%s" % (pformat(
            self.operations), pformat(self.closure))
        return s

    #@profile
    async def get_last_revision(self, retry=0):
        return
        try:
            async with self.session.get(url=url.format(self.fileId),
                                        headers=self.headers,
                                        timeout=timeout) as response:
                code = response.status
                if code != 200:
                    if retry > 2:
                        return -1
                    logger.debug("can't get last revision, sleeping ")
                    await asyncio.sleep(random.uniform(0, 10))
                    await self.get_last_revision(retry=retry + 1)
                    return 0
                else:
                    rev = await response.text()
                    rev = json.loads(rev)
                    self.last_revision_id = rev["revisions"][-1]["id"]
                    logger.debug("last revision id %s", self.last_revision_id)
                    return 0
        except:
            logger.debug("cannot get last revision id")



if __name__ == '__main__':

    path = list(range(20))
    closure = []
    for c, i in enumerate(path):
        for c1, i1 in enumerate(path[c:]):
            child = i1
            parent = i
            depth = c1

            closure.append((child, parent, depth))

    print(pformat(closure))
