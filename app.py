# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pprint import PrettyPrinter
import plotly.express as px
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from math import log
from dash.dependencies import Input, Output
from pprint import PrettyPrinter

HT_BINS = 20
zoomHist = [datetime.now(), datetime.now()]
pp = PrettyPrinter(indent=3)

def gen_margin(l= 50, r=5, b = 50, t = 50):
    return {
        'l':l, 'r': r, 'b': b, 't': t
    }


mwdat = 0
csvdata = 0


pointSelected = False

with open('maxwords.pickle', 'rb') as mw:
    mwdat = pickle.load(mw)
with open('csvdata.pickle', 'rb') as cv:
    csvdata = pd.DataFrame(pickle.load(cv))


pp.pprint(csvdata.index)
def genOptList(cols):
    ret = []
    ret.append(dict(label="empty", value="empty"))
    for c in cols:
        ret.append(dict(label=c, value=c))

    return ret

pp = PrettyPrinter(indent=3)


# Sets up activity bubble graph
activity = dict(time=[], files=[], marker_size=[])
hists = {}
for c in csvdata.columns:
    t = csvdata[c].dropna().index
    
    #Generate timestamp list
    times = [i.timestamp() for i in t]
    histogram_result = list(np.histogram(times, HT_BINS))

    #TIMEDELTA bug?
    bins = [datetime.fromtimestamp(i)+timedelta(hours = 8) for i in histogram_result[1]]

    hists[c] = (histogram_result[0], bins)



    if(len(t) > 0):
        activity["time"].append(t[-1])
        activity["files"].append(c)
     #   activity["marker_size"].append(log(max(csvdata.loc[t[-1], c], 1)))
      #  activity["marker_size"].append(len(t))
        activity["marker_size"].append(10)


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
        't':0,
        'r':0
    }
}
)


# Generates option list
optsList = genOptList(csvdata.columns)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        dcc.Graph(
            id="fList",
            figure=fListFig
        ), dcc.Dropdown(
            id="dropdown",
            options=genOptList(csvdata),
            value="empty"
        )
    ], className = "four columns",
    style = {
        'margin': gen_margin(b = 100)
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
    ], className = "four columns")
])


@app.callback(
    [Output("lineWord", "figure"),Output("histogram", "figure")],
    [Input("dropdown", "value")])
def update_figure(value):
    if(value == "empty"):
        value = activity["files"][0]

    print("updatae %s" % value)

    wordData = csvdata[value].dropna().values.tolist()
    timeData = csvdata[value].dropna().index.tolist()

    lineGraph = go.Figure(
        data=[dict(
            x=timeData,
            y=wordData,
            mode = "markers",
            marker_size = 10
        )],
        layout=dict(
            title=value + " Word Graph",
            margin = gen_margin(l = 50, b=50, t=50, r=0)
        )
    )

    pp.pprint(hists[value])
    hist = go.Figure(
        go.Bar(
            y = hists[value][0],
            x= hists[value][1]
        ),
        layout = {
            'title': "Histogram",
            'margin': gen_margin()
        }
    )
    return lineGraph, hist


@app.callback(
    Output("dropdown", "value"),
    [Input("fList", "hoverData"), Input("fList", "selectedData")])
def update_from_click(hover, click):
    if(hover == None and click == None):
        return "empty"

    if(click != None):
        print(click)
        return click["points"][0]["x"]
    else:
        print(click)
        return hover["points"][0]["x"]



@app.callback(
    [Input("histogram", "relayoutData")])
def update_zoom_params(zoom):
    zoomHist[0] = zoom["xaxis.range[0]"]
    zoomHist[1] = zoom["xaxis.range[1]"]
    #TODO: redo histogram for more accuracy


if __name__ == '__main__':
    app.run_server(debug=True)
