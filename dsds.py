from processing.get_files import loadFiles
import os
import pickle
import logging
import secrets

logger = logging.getLogger(__name__)


def start(gdoc_threads = None, workers = None, alt = False):
    if gdoc_threads:
        from processing import gdoc
        gdoc.threads = gdoc_threads
    if workers:
        from processing import get_files
        get_files.workerInstances = workers

    uid = "t" + secrets.token_urlsafe(3)

    #fileid = "1ytJocI9f4gvmpnwLNNfpQzRPhcFs5EzR"
    fileid = "0B4Fujvv5MfqbVElBU01fZUxHcUk"

    #Folders test
    #    fileid = "0Bx5kvRIrXW4JOHlPRm96cVcySTg"
    fileid = "root"

    data_path = os.environ["HOMEDATAPATH"]
    if alt:
        creds = pickle.load(open(os.path.join(data_path , 'creds1.pickle'), 'rb'))
    else:
        creds = pickle.load(open(os.path.join(data_path , 'creds.pickle'), 'rb'))
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, data_path, fileid, creds)


if __name__ == '__main__':
    import sys
    import getopt

    opts, nonargs = getopt.getopt(sys.argv[1:], 'mt:w:')

    threads = 2
    workers = 2
    alt = False

    for x in opts:
        if x[0] == '-t':
            threads = int(x[1])
        if x[0] == '-m':
            alt = True
        if x[0] == '-w':
            workers = int(x[1])


    start(gdoc_threads = threads, workers = workers, alt = alt)
