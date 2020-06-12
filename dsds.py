from processing.get_files import loadFiles
import os
import pickle
import logging
import secrets

logger = logging.getLogger(__name__)


def start(gdoc_threads = None, workers = None):

    print(gdoc_threads, workers)

    if gdoc_threads:
        from processing import gdoc
        gdoc.threads = gdoc_threads
    if workers:
        from processing import get_files
        get_files.workerInstances = workers

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
    import sys
    if len(sys.argv) == 3:
        start(gdoc_threads = int(sys.argv[1]), workers = int(sys.argv[2]))
    else:
        start()
