import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.dash import no_update
from flaskr.dashapp.dash_functions import *
from flaskr.flask_config import CONF


class Loader:
    pydocPath = None
    @classmethod
    def setpdpath (cls, _pydocPath):
        print("set pd")
        cls.pydocPath = _pydocPath

    @classmethod
    def loadcsv (cls, path):
        return pd.read_pickle(path + 'collapsedFiles_p.pickle')

    @classmethod
    def loadActivity (cls, path):
        return pd.read_pickle(path +  'activity.pickle')

    @classmethod
    def loadHists(cls, path):
        return pd.read_pickle( path + 'hists.pickle')


#Takes as params the dash-app, to register callbacks


def url_to_path(url):
    hdpath = CONF.HOMEDATAPATH
    return hdpath + url[6:] + '/'

def register_callback(app):
    print("register cb")
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
        Output("lineWord", "figure"),
        [ Input("dropdown", "value")],
        [ State("url", 'pathname')])
    def update_lineGraph(value, pathname):

        pathname = url_to_path(pathname)

        csvdata = Loader.loadcsv(pathname)
        activity = Loader.loadActivity(pathname)
        hists = Loader.loadHists(pathname)


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
        Output("histogram", "figure"),
        [Input("reset_histogram", "n_clicks"),
        Input("lineWord", "figure")],
        [State("histogram", "relayoutData"),
        State("dropdown", "value"),
        State("url", "pathname")]
    )
    def update_histogram(button, lineWord, zoomData, ddvalue, pathname):
        pathname = url_to_path(pathname)
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
            timesEdited = Loader.loadcsv(pathname).loc[ddvalue].index
            histData = redo_Histogram(timesEdited, pd.to_datetime(x_range[0]),
                pd.to_datetime(x_range[1]))
        else:
            histData = Loader.loadHists(pathname)[ddvalue]

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
        Output("primary", "children"),
        [Input("url", "pathname")]
    )
    def return_layout(path):
        path = url_to_path(path)

        print("printing layout: ", path)

        return [html.Div([
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
            ], className = "six columns")
            ]


