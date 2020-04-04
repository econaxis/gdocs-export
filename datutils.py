import pandas as pd
import numpy as np
import pickle
from math import log
from datetime import datetime
import google.oauth2.credentials
import google_auth_oauthlib.flow

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']

def authorization( homePath,scopes = SCOPES, user_id = "default"):
    creds = None
    APIKeyPath = homePath + "/secret/credentials.json"
    fileName = "data/" + user_id + "/secrets/token.pickle"
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            APIKeyPath, scopes)
    flow.redirect_uri = 'http://localhost'
    authorization_url , state = flow.authorization_url(access_type = 'offline', include_granted_scopes = 'true')
    return authorization_url

    if os.path.exists(fileName):
        with open(fileName, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                APIKeyPath, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(fileName, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def formatData():
    rdata = pickle.load(open('revdata.pickle', 'rb'))

    ind = pd.MultiIndex.from_tuples(rdata.keys())
    data = pd.DataFrame(rdata.values(), index = ind, columns = ["Type"])

    len_data = len(data.index.levels[1])
    sumDatesIndex = pd.MultiIndex.from_product([["sumDates"], data.index.levels[1]])
    sumDatesFrame = pd.DataFrame([1]*len_data, index = sumDatesIndex, columns = ["Type"])

    data = data.append(sumDatesFrame)

    data.to_pickle('data.pickle')



def activity_gen():
    data = pd.read_pickle('data.pickle')
    hists = {}
    activity = dict(time=[], files=[], marker_size=[])
    for f in data.index.levels[0]:
        timesForFile = data.loc[f].index
        activity["time"].append(data.loc[f].index[-1])
        activity["files"].append(f)
        activity["marker_size"].append(log(len(timesForFile), 1.3))
        hists[f] = [0, 0]
        hists[f][0], bins = np.histogram([i.timestamp() for i in timesForFile], bins = 'auto')
        hists[f][1] = [datetime.fromtimestamp(i) for i in bins]
    pickle.dump(activity, open('activity.pickle', 'wb'))
    pickle.dump(hists, open('hists.pickle', 'wb'))
