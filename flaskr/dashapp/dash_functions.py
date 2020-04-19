# For use with dash app.py
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from math import log
from dash.dependencies import Input, Output, State
from dash.dash import no_update
from pprint import PrettyPrinter
from processing.models import Owner, Dates, Files, Filename
from sqlalchemy.sql import func
from flaskr.flask_config import cache
from processing.sql import scoped_sess as db
import flask


#Maps fileid to index
idIndexMapper = {}

#maps index to fileid
namesList = [None] * 5000


pprint = PrettyPrinter(indent=4).pprint




@cache.memoize()
def genOptList(userid):
    #Get list of all filenames and fileids by owner id

    #names = db.query(Files.id, Filename.fileName).join(Filename).join(Owner).filter( Owner.name == userid).all()

    #DEBUG: no owner filter
    names = db.query(Filename.fileName, Files.id).join(Files).join(Owner).all()

    ret = []
    for c in names:
        #Label is filename, value is file id
        ret.append(dict(label=c[0], value=c[1]))

    ret.append(dict(label="All", value="All"))
    return ret




@cache.memoize()
def getNormalBubbleData(sess, userid):

    #Function should ideally be run only once per user, because of cache.memoize

    #Get all the files with their counts of edits and last modified time
    allFiles = sess.query(Files.id, Dates.moddate).join(Dates).join(Owner).filter(Owner.name == userid).subquery()

    #TESTING: no owner query
    allFiles = sess.query(Files.id, Dates.moddate).join(Dates).join(Owner).subquery()

    #Group by id
    times = sess.query(allFiles.c.id, func.count('*').label('count'),
            func.max(allFiles.c.moddate).label('max')).group_by(allFiles.c.id).subquery()


    #Join id to filename
    #per element in count: (filename, file.id, count, last mod date)
    count = sess.query(Filename.fileName, times.c.id, times.c.count, times.c.max).join(times).all()


    activity = {}
    activity["time"] = [x[3] for x in count]
    activity["files"] = [x[0] for x in count]
    activity["marker"] = [log(x[2], 2) * 1.3 for x in count]

    #Custom represents file.id
    activity["custom"] = [x[1] for x in count]

    for counter, f in enumerate(activity["custom"]):
        # idIndexMapper indexes filename and corresponding index
        # namesList indexes index by corresponding filename
        # Used for quick references and changing current selection on graph
        idIndexMapper[f] = counter
        namesList[counter] = f

    _fListFig = go.Figure(
        data=go.Scatter(
            y=activity["time"],
            x=activity["files"],
            mode="markers",
            marker_size=activity["marker"],
            selected={
                'marker': {
                    'color': 'darkorange'}},
            customdata = activity["custom"]
            ),

        layout={
            'clickmode': 'event+select',
            'margin': gen_margin(),
            'title': "BubbleChart",
            'xaxis': {
                'visible': False}})

    return _fListFig


def gen_fListFig(sess, userid, slPoints=None):
    # Get the list of all filenames with their last modified date
    fListFig = getNormalBubbleData(sess, userid)

    if(slPoints):
        # Set selectedpoints if there exists slPoints param
        fListFig["data"][0]["selectedpoints"] = slPoints
    return fListFig


def gen_margin(l=5, r=5, b=20, t=70):
    return { 'l': l, 'r': r, 'b': b, 't': t }
