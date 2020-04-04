import pandas as pd
import numpy as np
import pickle
from math import log
from datetime import datetime



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