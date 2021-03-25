import certifi
import time
from configlog import tracer
import random
import aiohttp
import asyncio
import ujson as json
import logging


from collections import namedtuple


from threading import Lock

logger = logging.getLogger(__name__)



timeout = aiohttp.ClientTimeout(total=15)



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

    async def async_init(self, name, fileId, session, headers, path, last_revision_id):
        self.operations = []
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

    async def _download_details(self):

        logger.debug("received job for %s", self.fileId)



    def __repr__(self):
        s = "GDoc Object\n\t%s\n\t%s" % (pformat(
            self.operations), pformat(self.closure))
        return s

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
