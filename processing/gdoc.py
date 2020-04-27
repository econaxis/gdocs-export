import requests
import textwrap
import time
from pprint import pformat
import random
import aiohttp
import asyncio
import ujson as json
import logging


from types import SimpleNamespace

logger = logging.getLogger(__name__)

base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'
url = 'https://www.googleapis.com/drive/v3/files/{}/revisions'

timeout = aiohttp.ClientTimeout(total=10)

class GDoc():

    __slots__ = ['last_revision_id', 'fileId', 'session', 'headers']

    def __init__(self):
        pass

    async def async_init(self, fileId, session, headers):
        #Returns list of dates

        self.last_revision_id = 1

        logger.debug("async init called")
        self.fileId = fileId
        self.session = session
        self.headers = headers
        self.last_revision_id = 1

        await self.get_last_revision()


        logger.debug("after await %s", self.last_revision_id)



    async def get_last_revision(self, retry = False):

        try:
            async with self.session.get(url=url.format(self.fileId), 
                    headers=self.headers, timeout = timeout) as response:
                code = response.status
                if code != 200:
                    logtext = await response.text()
                    logtext = textwrap.wrap(logtext, 1000)
                    [logger.log(1, pformat(x)) for x in logtext]

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
            logger.exception("cannot get last revision id")


    def download_details(self,  pipe):

        logger.info("received job for %s",self.fileId)

        dates = []
        #Retries
        for i in range(1, 3):
            url = base_url.format(file_id=self.fileId, end=self.last_revision_id)

            dates = []

            response = SimpleNamespace(text = "Blank Filler. This will show when response is undefined")
            logger.info("get url: %s", url)
            try:
                logger.info("starting url get")
                response = requests.get(url = url, headers = self.headers, timeout = 5)
                logger.info('url get sucess')
                assert response.status_code == 200
            except:
                logger.info("%s unable, sleeping up to %d", self.fileId[0:5], 20*i)
                time.sleep(random.uniform(5, 20*i))
                continue

            text = response.text

            print("starting json load")
            revision_details = json.loads(text[5:])

            dates = [None]*len(revision_details['changelog'])

            for count,x in enumerate(revision_details['changelog']):
                logger.debug("processing dates, for %s", self.fileId)
                dates[count] = x[1]/1e3

            break

        print(dates)

        pipe.send(dates)

        counter = 1

        while not pipe.poll(0.1):
            logger.debug("resending for %s", self.fileId[0:5])
            pipe.send(dates)
            counter +=1
            time.sleep(6*counter)

            if counter > 10:
                pipe.send(dates)
                pipe.close()
                return

        logger.debug("pipe received: %s correct: %s after %d", pipe.recv(), self.fileId[0:5], counter)

        pipe.close()

        return
