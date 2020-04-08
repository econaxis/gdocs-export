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
from flask_caching import Cache
from pprint import PrettyPrinter

path  = None

def setPath(_path):
    global path
    path = _path

def serializeDT(d) :
    return o.__str__()

def genOptList(path):
    cols=pd.read_pickle(path + 'collapsedFiles_p.pickle').index.levels[0].to_list()
    ret = []
    ret.append(dict(label="sumDates", value="sumDates"))
    for c in cols:
        ret.append(dict(label=c, value=c))
    return ret

def gen_margin(l= 5, r=5, b = 20, t = 70):
    return {
        'l':l, 'r': r, 'b': b, 't': t
    }
def gen_fListFig(path):
    activity = pd.read_pickle(path + 'activity.pickle')
    fListFig = go.Figure(data=go.Scatter(
        y=activity["time"],
        x=activity["files"],
        mode="markers",
        marker_size=activity["marker_size"]   
    ),
        layout={
        'clickmode': 'event+select',
        'margin' : {
            'l':50,
            'b':100,
            't':50,
            'r':0
        }
    }
    )
    return fListFig
def get_layout():
    global path
    return html.Div([
        html.Div([
            dcc.Graph(
                id="fList",
                figure = gen_fListFig(path)
            ), dcc.Dropdown(
                id="dropdown",
                options=genOptList(path),
                value="sumDates"
            )
            ], className = "six columns",
            style = {
            'margin': gen_margin(l = 20)
            }
        ),
        html.Div([
            dcc.Graph(
                id = "histogram"
            ),
            html.Button(
                "Reset Histogram",
                id = "reset_histogram"
            )
        ], className = "six columns"),
        html.Div(
            id = "csvdata", style = {'display': 'none'}
        ),
        html.Div(
            id = "zoomInfo", style = {'display': 'none'}
        ),
        html.Div([
            dcc.Graph(
                id="lineWord"
            )
        ], className = "four columns",
        style={'display':'none'})

    ])

def redo_Histogram(times, minDate, maxDate):
    hists = [0, 0]
    hists[0], bins = np.histogram([i.timestamp() for i in times], 30,
        range = (minDate.timestamp(), maxDate.timestamp()))
    hists[1] = [datetime.fromtimestamp(i) for i in bins]
    return hists

