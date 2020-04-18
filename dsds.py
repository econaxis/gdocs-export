from processing.get_files import loadFiles
from google.oauth2 import service_account
import pickle
import os

if __name__ == "__main__":
    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"
    homePath =  "/home/henry/pydocs/"

    fileid = "0B4Fujvv5MfqbeTVRc3hIbXRfNE0"

    if("DBGHPATH" in os.environ):
        homePath = os.environ["DBGHPATH"]
    workingPath =  homePath + 'data/' + uid + '/'
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    CREDENTIAL_FILE = 'service.json'
    SCOPE = ['https://www.googleapis.com/auth/drive']

    loadFiles(uid, workingPath, fileid, creds)
