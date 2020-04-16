import dash
import dash_core_components as dcc
from processing.models import Owner, Files, Dates
from processing.sql import scoped_sess
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
import pprint
from dash.dash import no_update
from flask import current_app
import flask
from flaskr.dashapp.dash_functions import *
from flaskr.flask_config import CONF

from processing.sql import sess
from processing.models import Owner, Files, Dates

from sqlalchemy.orm import joinedload

pp = PrettyPrinter(indent=4)

test = {}
test["workingPath"] = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
test["userid"] = "527e4afc-4598-400f-8536-afa5324f0ba4"


def register_callback(app):

    @app.callback(
        Output("histogram", "figure"),
        [Input("reset_histogram", "n_clicks"),
        Input("timeck", "value"),
        Input("dropdown", "value")]
    )
    def update_histogram(button, times, ddvalue):
        dates_uf = None
        print(ddvalue)
        if(ddvalue == 'All'):
            #If all dates are wanted, query is different for more optimization
            dates_uf = sess.query(Dates).join(Files).filter(Files.parent_id==test["userid"]).all()
        else:
            dates_uf = sess.query(Files).options(joinedload(Files.children)) \
                    .filter(Files.parent_id == test["userid"]).filter(Files.fileName==ddvalue) \
                    .first().children



        tickformat=""
        if(times):
            dates = [x.moddate.replace(year=2000, month = 1, day = 1) for x in dates_uf]
            tickformat="%H:%M"
        else:
            dates = [x.moddate for x in dates_uf]

        return go.Figure(
            data = [go.Histogram(x=dates, nbinsx=60)],
            layout= dict(
                margin=gen_margin(),
                xaxis = dict(
                    tickformat=tickformat,
                    type="date"
                )
            )
        )

    @app.callback(
        Output("fList", "figure"),
        [Input("url", "pathname")])
    def retfList(value):
        return gen_fListFig(scoped_sess, test["userid"])

    @app.callback(
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def getoptions(value):
        return genOptList(test["userid"])


    @app.callback(
        Output("dropdown", "value"),
        [Input("fList", "hoverData"), Input("fList", "selectedData")])
    def update_from_click(hover, click):
        if(hover == None and click == None):
            return None

        if(click != None):
            return click["points"][0]["x"]
        else:
            return hover["points"][0]["x"]




class Loader:
    pydocPath = None
    @classmethod
    def setpdpath (cls, _pydocPath):
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

