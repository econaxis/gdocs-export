# -*- coding: utf-8 -*-
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
pp = PrettyPrinter(indent=3)

def serializeDT(d) :
    return o.__str__()

def genOptList():
    cols=pd.read_pickle('csvdata.pickle').index.levels[0].to_list()
    ret = []
    ret.append(dict(label="sumDates", value="sumDates"))
    for c in cols:
        ret.append(dict(label=c, value=c))
    return ret


def gen_margin(l= 5, r=5, b = 20, t = 70):
    return {
        'l':l, 'r': r, 'b': b, 't': t
    }
def gen_fListFig():
    activity = pd.read_pickle('activity.pickle')
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
CACHE_CONFIG = {
    'DEBUG': True,
    "CACHE_TYPE": "filesystem", # Flask-Caching related configs.
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_DIR": 'cache_data'
}
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div([
    html.Div([
        dcc.Graph(
            id="fList",
            figure = gen_fListFig()
        ), dcc.Dropdown(
            id="dropdown",
            options=genOptList(),
            value="sumDates"
        )
        ], className = "four columns",
        style = {
        'margin': gen_margin(l = 20)
        }
    ),
    html.Div([
        dcc.Graph(
            id="lineWord"
        )
    ], className = "four columns"),
    html.Div([
        dcc.Graph(
            id = "histogram"
        ),
        html.Button(
            "Reset Histogram",
            id = "reset_histogram"
        )
    ], className = "four columns"),

    #Hidden Div for storing information
    html.Div(
        id = "csvdata", style = {'display': 'none'}
    ),
    html.Div(
        id = "zoomInfo", style = {'display': 'none'}
    )
])

cache = Cache()
cache.init_app(app.server, config = CACHE_CONFIG)

@cache.memoize()
def loadcsv ():
    return pd.read_pickle('csvdata.pickle')
@cache.memoize()
def loadActivity ():
    return pd.read_pickle('activity.pickle')
@cache.memoize()    
def loadHists():
    return pd.read_pickle('hists.pickle')






# Sets up activity bubble graph


def redo_Histogram(file, minDate, maxDate):
    csvdata = loadcsv()
    hists =[]
    timesForFile = csvdata.loc[file].index
    hists = [0, 0]
    hists[0], bins = np.histogram([i.timestamp() for i in timesForFile], 30,
        range = (minDate.timestamp(), maxDate.timestamp()))
    hists[1] = [datetime.fromtimestamp(i) for i in bins]
    return hists


@app.callback(
    Output("histogram", "figure"),
    [Input("reset_histogram", "n_clicks"),
    Input("lineWord", "figure")],
    [State("histogram", "relayoutData"),
    State("dropdown", "value")]
)
def update_histogram(button, lineWord, zoomData, ddvalue):
    ctx = dash.callback_context
    fileChanged = False

    for c in ctx.triggered:
        if(c["prop_id"].split('.')[0] == 'lineWord'):
            #Value of file changed, not Zoom. Therefore, set
            #bool fileChanged to True
            fileChanged = True
            break

    x_range = [0, 0, False]
    histData = [0, 0]
    if(not fileChanged and zoomData != None and "xaxis.range[0]" in zoomData):
        x_range[0] = zoomData["xaxis.range[0]"]
        x_range[1] = zoomData["xaxis.range[1]"]
        histData = redo_Histogram(ddvalue, pd.to_datetime(x_range[0]),
            pd.to_datetime(x_range[1]))
    else:
        histData = loadHists()[ddvalue]

    return go.Figure(
        go.Bar(
            y = histData[0],
            x= histData[1]
        ),
        layout = {
            'title': "Histogram",
            'margin': gen_margin()
        }
    )


        



@app.callback(
    Output("lineWord", "figure"),
    [Input("dropdown", "value")])
def update_lineGraph(value):
    csvdata = loadcsv()
    activity = loadActivity()
    hists = loadHists()


    wordData = csvdata.loc[value, 'Type'].dropna().values.tolist()
    timeData = csvdata.loc[value, 'Type'].dropna().index.tolist()

    lineGraph = go.Figure(
        data=[dict(
            x=[pd.to_datetime(i, unit = 's') for i in timeData],
            y=wordData,
            mode = "markers",
            marker_size = 10
        )],
        layout=dict(
            title=value + " Word Graph",
            margin = gen_margin()
        )
    )
    
    return lineGraph


@app.callback(
    Output("dropdown", "value"),
    [Input("fList", "hoverData"), Input("fList", "selectedData")])
def update_from_click(hover, click):
    if(hover == None and click == None):
        return "sumDates"

    if(click != None):
        return click["points"][0]["x"]
    else:
        return hover["points"][0]["x"]


@app.callback(
    Output("zoomInfo", "children"),
    [Input("histogram", "relayoutData")])
def update_zoom_params(zoom):
    zoomHist = [0, 0]
    if(zoom == None or "xaxis.range[0]" not in zoom):
        zoomHist[0] = datetime.now().__str__()
        zoomHist[1] = datetime.now().__str__()
        return json.dumps(zoomHist)

    zoomHist[0] = zoom["xaxis.range[0]"]
    zoomHist[1] = zoom["xaxis.range[1]"]

    return json.dumps(zoomHist)
    #TODO: redo histogram for more accuracy


if __name__ == '__main__':
    app.run_server(debug=True)
