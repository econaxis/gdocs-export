# For use with dash app.py
import dash
import dash_core_components as dcc
from functools import lru_cache
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
from processing.models import Owner, Dates, Files
from sqlalchemy.sql import func
from flaskr.flask_config import cache
from processing.sql import scoped_sess as db
import flask

idList = {}
namesList = [None] * 5000
pprint = PrettyPrinter(indent=4).pprint


def gen_fListFig(sess, userid, slPoints=None):
    # Get the list of all filenames with their last modified date
    fListFig = getNormalBubbleData(sess, userid)

    if(slPoints):
        # Set selectedpoints if there exists slPoints param
        fListFig["data"][0]["selectedpoints"] = slPoints
    return fListFig


@cache.memoize()
def genOptList(uid):
    names = db.query(
        Files.fileId).join(Owner).filter(
        Owner.name == uid).all()
    ret = []
    for c in names:
        ret.append(dict(label=c[0], value=c[0]))

    ret.append(dict(label="All", value="All"))
    return ret


def gen_margin(l=5, r=5, b=20, t=70):
    return {
        'l': l, 'r': r, 'b': b, 't': t
    }


@cache.memoize()
def getNormalBubbleData(sess, userid):
    gt = sess.query(Files.fileId, Dates.moddate).join(
        Dates).filter(Files.parent_id == userid).subquery()

    count_sq = sess.query(gt.c.fileId, func.count('*').label('count'), func.max(gt.c.moddate).label('max')) \
        .group_by(gt.c.fileId).limit(5000).subquery()

    count = sess.query(Files.fileId, count_sq.c.count, count_sq.c.max) \
        .join(count_sq, count_sq.c.fileId == Files.fileId).all()
    activity = {}
    activity["time"] = [x[2] for x in count]
    activity["files"] = [x[0] for x in count]
    activity["marker"] = [log(x[1], 3) * 2 for x in count]

    for counter, f in enumerate(activity["files"]):
        # idList indexes filename and corresponding index
        # namesList indexes index by corresponding filename
        # Used for quick references and changing current selection on graph
        idList[f] = counter
        namesList[counter] = f
    pickle.dump(idList, open('idlist', 'wb'))
    pickle.dump(activity["files"], open('files', 'wb'))
    _fListFig = go.Figure(
        data=go.Scatter(
            y=activity["time"],
            x=activity["files"],
            mode="markers",
            marker_size=activity["marker"],
            selected={
                'marker': {
                    'color': 'darkorange'}}),
        layout={
            'clickmode': 'event+select',
            'margin': gen_margin(),
            'title': "BubbleChart",
            'xaxis': {
                'visible': False}})
    return _fListFig
