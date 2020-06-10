from processing.get_files import loadFiles
import os
import pickle
import logging
import secrets

logger = logging.getLogger(__name__)


def start():
    logger.info('start')

    uid = "t" + secrets.token_urlsafe(3)

    #fileid = "1ytJocI9f4gvmpnwLNNfpQzRPhcFs5EzR"
    fileid = "0B4Fujvv5MfqbVElBU01fZUxHcUk"

    #Folders test
    #    fileid = "0Bx5kvRIrXW4JOHlPRm96cVcySTg"
    fileid = "root"

    workingPath = os.environ["HOMEDATAPATH"]
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, workingPath, fileid, creds)


if __name__ == '__main__':
    start()
