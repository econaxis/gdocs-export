from processing.get_files import loadFiles
import pickle
import os
import logging
from flaskr.flask_config import Config

logger = logging.getLogger(__name__)


def start():
    logger.info('start')

    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"

    homePath=Config.HOMEPATH
    #fileid = "1ytJocI9f4gvmpnwLNNfpQzRPhcFs5EzR"
    fileid = "0B4Fujvv5MfqbVElBU01fZUxHcUk"
    #fileid = "root"


    workingPath = Config.HOMEDATAPATH
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, workingPath, fileid, creds)


if __name__ == '__main__':
    start()
