from processing.get_files import loadFiles
import pickle
import os
import logging
import secrets
from flaskr.flask_config import Config

logger = logging.getLogger(__name__)


def start():
    logger.info('start')

    uid = "t" + secrets.token_urlsafe(3)

    homePath = Config.HOMEPATH
    #fileid = "1ytJocI9f4gvmpnwLNNfpQzRPhcFs5EzR"
    fileid = "0B4Fujvv5MfqbVElBU01fZUxHcUk"

    #Folders test
    #    fileid = "0Bx5kvRIrXW4JOHlPRm96cVcySTg"
    fileid = "root"

    workingPath = Config.HOMEDATAPATH
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, workingPath, fileid, creds)


if __name__ == '__main__':
    start()
