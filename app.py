# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pprint import PrettyPrinter
import plotly.express as px
import pickle
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from math import log
from dash.dependencies import Input, Output
from dash.dash import no_update
from pprint import PrettyPrinter

HT_BINS = 20
pp = PrettyPrinter(indent=3)

def gen_margin(l= 50, r=5, b = 50, t = 50):
    return {
        'l':l, 'r': r, 'b': b, 't': t
    }


def genOptList():
    cols=pd.read_pickle('csvdata.pickle').index.levels[0].to_list()
    ret = []
    ret.append(dict(label="empty", value="empty"))
    for c in cols:
        ret.append(dict(label=c, value=c))
    return ret

# Sets up activity bubble graph

#TODO set up activity and hists 


def df_json(df):
    ind = df.index.to_series().to_json(orient = 'values')
    return [ind, df.reset_index(drop=True).to_json()]

def json_df(js):
    tups = json.loads(js[0])
 #   for i in tups:
  #      i[1] = pd.to_datetime(i[1], unit = 'ms')
    index = pd.MultiIndex.from_tuples(tups)
    return pd.read_json(js[1]).set_index(index)

def loadcsv ():
    return pd.read_pickle('csvdata.pickle')
def loadActivity ():
    return pd.read_pickle('activity.pickle')
def loadHists():
    return pd.read_pickle('hists.pickle')


def activity_gen():
    csvdata = loadcsv()
    hists = {}
    activity = dict(time=[], files=[], marker_size=[])

    for f in csvdata.index.levels[0]:
        timesForFile = csvdata.loc[f].index

        activity["time"].append(csvdata.loc[f].index[-1])
        activity["files"].append(f)
        activity["marker_size"].append(log(len(timesForFile), 1.2))
        hists[f] = [0, 0]
        hists[f][0], bins = np.histogram([i.timestamp() for i in timesForFile], bins = 'auto')
        hists[f][1] = [datetime.fromtimestamp(i) for i in bins]


    pickle.dump(activity, open('activity.pickle', 'wb'))
    pickle.dump(hists, open('hists.pickle', 'wb'))
    #gen_fListFig()
    

def redo_Histogram(file, minDate, maxDate):
    csvdata = loadcsv()
    hists =[]
    timesForFile = csvdata.loc[file].index
    hists = [0, 0]
    hists[0], bins = np.histogram([i.timestamp() for i in timesForFile], 30,
        range = (minDate.timestamp(), maxDate.timestamp()))
    hists[1] = [datetime.fromtimestamp(i) for i in bins]

    return hists

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
   
    html.Div([
        dcc.Graph(
            id="fList"
        ), dcc.Dropdown(
            id="dropdown",
            options=genOptList(),
            value="empty"
        )
    ], className = "four columns",
    style = {
        'margin': gen_margin(b = 100, l = 20)
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
        )
    ], className = "four columns"),

    #Hidden Div for storing information
    html.Div(
        id = "csvdata", style = {'display': 'none'},
        children = [activity_gen()]
    ),
    html.Div(
        id = "zoomInfo", style = {'display': 'none'}
    ),
    html.Div(
        id = "activityHistStore", style = {'display': 'none'}
    )  
])




@app.callback(
    Output("fList", "figure"),
    [Input("csvdata", "children")]
)
def gen_fListFig(value):
    ("flist")
    activity = loadActivity()

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


@app.callback(
    [Output("lineWord", "figure"),Output("histogram", "figure")],
    [Input("dropdown", "value"), Input('zoomInfo', 'children')])
def update_figure(value, zinfo):
    ctx = dash.callback_context
    csvdata = loadcsv()
    activity = loadActivity()
    hists = loadHists()


    if(zinfo !=None):
        zinfo = json.loads(zinfo)

    if(value == "empty"):
        value = activity["files"][0]


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
            margin = gen_margin(l = 50, b=50, t=50, r=0)
        )
    )



    changedZoom = False
    if(ctx.triggered):
        for i in ctx.triggered:
            if(i["prop_id"].split('.')[0]=="zoomInfo"):
                changedZoom = True
                break;

    histData = None
    #TODO
    if(changedZoom):
        histData = redo_Histogram(value, pd.to_datetime(zinfo[0]), pd.to_datetime(zinfo[1]))
        pp.pprint(histData)
        if(histData[0].max() ==0):
            #Reset to original Histogram if no bins (zoom too high)
            histData = hists[value]
    else:
        histData = hists[value]
    hist = go.Figure(
        go.Bar(
            y = histData[0],
            x= histData[1]
        ),
        layout = {
            'title': "Histogram",
            'margin': gen_margin()
        }
    )
    return [lineGraph, hist]


@app.callback(
    Output("dropdown", "value"),
    [Input("fList", "hoverData"), Input("fList", "selectedData")])
def update_from_click(hover, click):
    if(hover == None and click == None):
        return "empty"

    if(click != None):
        return click["points"][0]["x"]
    else:
        return hover["points"][0]["x"]


@app.callback(
    Output("zoomInfo", "children"),
    [Input("histogram", "relayoutData"), ])
def update_zoom_params(zoom):
    zoomHist = [0, 0]
    if(zoom == None or "xaxis.range[0]" not in zoom):
        zoomHist[0] = datetime.now()
        zoomHist[1] = datetime.now()
        return json.dumps(zoomHist)

    zoomHist[0] = zoom["xaxis.range[0]"]
    zoomHist[1] = zoom["xaxis.range[1]"]

    return json.dumps(zoomHist)
    #TODO: redo histogram for more accuracy


if __name__ == '__main__':
    app.run_server(debug=True)
