# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from pprint import PrettyPrinter
import plotly.express as px
import pickle
import pandas as pd
from dash.dependencies import Input, Output

def genOptList(cols):
    ret = []
    ret.append(dict(label = "empty", value = "empty"))
    for c in cols:
        ret.append(dict(label = c, value = c))

    return ret

pp = PrettyPrinter(indent=3)
htmap = 0
htmapFig=0





mwdat = 0
csvdata=0


with open('maxwords.pickle', 'rb') as mw:
    mwdat = pickle.load(mw)

with open('csvdata.pickle', 'rb') as cv:
    csvdata = pd.DataFrame(pickle.load(cv))

activity = pd.DataFrame(index = mwdat.index, columns = mwdat.columns)


optsList = genOptList (csvdata.columns)

pp.pprint(mwdat)

for i in mwdat.columns:
    for j in mwdat.index:
        if(mwdat.loc[j,i] > 0):
            activity.loc[j,i] = 20

htmap = activity.values.tolist()

htmapFig = go.Figure(data = go.Heatmap(
    z=htmap,
    y=activity.index,
    x=activity.columns
))



external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div([
    dcc.Graph(
        id = "heatmap",
        figure = htmapFig),
    dcc.Dropdown(
        id="dropdown",
        options=genOptList(csvdata),
        value = "empty"
    ),
    dcc.Graph(
        id = "lineWord"
    )

])

@app.callback(
    Output("lineWord", "figure"),
    [Input("dropdown", "value")])
def update_figure(value):
    print("updatae %s"%value)
    pp.pprint(csvdata)
    wordData = csvdata[value].dropna().values.tolist()
    timeData = csvdata[value].dropna().index.tolist()
    fig = dict(
        data = [
            dict(x = timeData, y = wordData)
        ],
        layout = dict(
            title = value + "Word Graph"
        )
    )
    return fig




if __name__ == '__main__':
    app.run_server(debug=True)