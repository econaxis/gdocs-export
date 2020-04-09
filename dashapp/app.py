# -*- coding: utf-8 -*-
from datutils.dash_functions import *
import flask


workingPath = "data/5a80b6d0-07bb-42c2-a023-15894be46026/"
pp = PrettyPrinter(indent=3)

CACHE_CONFIG = {
    'DEBUG': True,
    "CACHE_TYPE": "filesystem", # Flask-Caching related configs.
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_DIR": 'cache_data'
}
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, url_base_pathname = "/dash/")


#Imported from dash_functions module
setPath(workingPath)
app.layout = get_layout

cache = Cache()
cache.init_app(app.server, config = CACHE_CONFIG)

def loadcsv ():
    return pd.read_pickle(workingPath + 'collapsedFiles_p.pickle')
def loadActivity ():
    return pd.read_pickle(workingPath + 'activity.pickle')
def loadHists():
    return pd.read_pickle(workingPath + 'hists.pickle')

# Sets up activity bubble graph

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
        timesEdited = loadcsv().loc[ddvalue].index
        histData = redo_Histogram(timesEdited, pd.to_datetime(x_range[0]),
            pd.to_datetime(x_range[1]))
    else:
        histData = loadHists()[ddvalue]

    return go.Figure(
        go.Bar(
            y = histData[0],
            x= histData[1]
        ),
        layout = {
            'title': "Edits Histogram",
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
