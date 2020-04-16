#For use with dash app.py
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from pprint import PrettyPrinter
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from math import log
from dash.dependencies import Input, Output, State
from dash.dash import no_update
from pprint import PrettyPrinter
from processing.models import Owner, Dates, Files
from sqlalchemy.sql import func
from processing.sql import scoped_sess as db
import flask

pp = PrettyPrinter(indent = 4)

def serializeDT(d) :
    return o.__str__()

def genOptList(uid):
    names = db.query(Files.fileName).join(Owner).filter(Owner.name==uid).all()

    ret = []
    for c in names:
        ret.append(dict(label=c[0], value=c[0]))

    ret.append(dict(label="All", value = "All"))
    print(ret[0:3])
    return ret

def gen_margin(l= 5, r=5, b = 20, t = 70):
    return {
        'l':l, 'r': r, 'b': b, 't': t
    }
def gen_fListFig(sess, userid):

    #Get the list of all filenames with their last modified date
    
    gt = sess.query(Owner.name, Files.fileId, Files.fileName, Dates.moddate).filter(Owner.name == userid) \
        .join(Files, Files.parent_id == Owner.name).join(Dates, Dates.parent_id == Files.fileId).subquery()

    count = sess.query(gt.c.fileName, func.count('*'), func.max(gt.c.moddate)) \
        .group_by(gt.c.fileName).all()


    activity = {}
    activity["time"]= [x[2] for x in count]
    activity["files"] = [x[0] for x in count]
    activity["marker"] = [log(x[1], 3)*2 for x in count]

    fListFig = go.Figure(data=go.Scatter(
        y=activity["time"],
        x=activity["files"],
        mode="markers",
        marker_size=activity["marker"]
    ),
        layout={
        'clickmode': 'event+select',
        'margin': gen_margin(),
        'title' : "Bubble Chart",
        'xaxis': {
            'visible': False
        }
    }
    )

    print("done")
    return fListFig



def redo_Histogram(times, minDate, maxDate):
    hists = [0, 0]
    hists[0], bins = np.histogram([i.timestamp() for i in times], 30,
        range = (minDate.timestamp(), maxDate.timestamp()))
    hists[1] = [datetime.fromtimestamp(i) for i in bins]
    return hists

