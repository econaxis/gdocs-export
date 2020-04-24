import aiohttp
from datetime import datetime
import asyncio
import ujson as json
import logging

logger = logging.getLogger(__name__)

base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'
url = 'https://www.googleapis.com/drive/v3/files/{}/revisions'

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

        code = await self.get_last_revision()

        logger.debug("after await %s", self.last_revision_id)

        dates = await self.download_details(self.last_revision_id)

        return dates


    async def get_last_revision(self, retry = False):

        try:
            async with self.session.get(url=url.format(self.fileId), headers=self.headers) as response:
                code = response.status
                if code != 200:
                    logger.debug("code not 200")
                    #logger.debug(await response.text())
                    if retry:
                        return -1
                    await asyncio.sleep(7)
                    await self.get_last_revision(retry = True)
                else:
                    rev = await response.text()
                    rev = json.loads(rev)
                    self.last_revision_id = rev["revisions"][-1]["id"]
                    logger.debug("last revision id %s", self.last_revision_id)
                    return 0
        except:
            logger.exception("cannot get last revision id")


    async def download_details(self, endid):
        url = base_url.format(file_id=self.fileId, end=endid)

        try:
            async with self.session.get(url = url, headers = self.headers) as response:
                
                assert response.status == 200

                text = await response.text()
                revision_details = json.loads(text[5:])

                logger.log(1, revision_details['changelog'])

                dates = [None]*len(revision_details['changelog'])
                for count,x in enumerate(revision_details['changelog']):
                    dates[count] =datetime.fromtimestamp(x[1]/1e3) 

                return dates
        except:
            logger.exception("Cannot get revisions.json")
            return []
