from processing.get_files import loadFiles
import sys
from contextlib import redirect_stdout
import cProfile
from google.oauth2 import service_account
import pickle
import os
import configlog
import logging

logger = logging.getLogger(__name__)


def start():
    logger.debug("start")
    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"
    homePath = "/home/henry/pydocs/"

    fileid = "root"

    if("DBGHPATH" in os.environ):
        homePath = os.environ["DBGHPATH"]

    workingPath = homePath + 'data/' + uid + '/'
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    CREDENTIAL_FILE = 'service.json'
    SCOPE = ['https://www.googleapis.com/auth/drive']
    loadFiles(uid, workingPath, fileid, creds)

if __name__ =='__main__':
    start()
    cProfile.runctx('start()', globals = globals(), locals = locals())


