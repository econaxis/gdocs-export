import dash
import dash_core_components as dcc
from processing.models import Owner, Files, Dates
from processing.sql import scoped_sess as db
from processing.sql import scoped_sess
from datetime import datetime
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
import pprint
from dash.dash import no_update
from flask import current_app
import flask
from flaskr.dashapp.dash_functions import *
from flaskr.flask_config import CONF, cache

from processing.sql import sess
from processing.models import Owner, Files, Dates, Closure

from sqlalchemy.orm import joinedload
from sqlalchemy import and_
import pprint


pprint = PrettyPrinter(indent=4).pprint


test = {}
test["workingPath"] = "/home/henry/pydocs/data/527e4afc-4598-400f-8536-afa5324f0ba4/"
test["userid"] = "527e4afc-4598-400f-8536-afa5324f0ba4"


def register_callback(app):
    @app.callback(
        Output("fList", "figure"),
        [Input('reset_histogram', "n_clicks")],
        [State("fList", "selectedData")]
    )
    def updateflist(value,clicked):
        print("dsds"*100)
        pprint(clicked)
        #Return selected point in fileName
        selectedPoint = clicked["points"][0]['x']


        dts = datetime.now()
        immediateParent = db.query(Closure.parent).filter(and_(Closure.depth ==1,
            Closure.child==selectedPoint, Closure.owner_id==test["userid"])).limit(1).subquery()

        sibs = db.query(Files.fileName).join(Closure, Closure.child==Files.fileName) \
                .filter(Closure.parent==immediateParent.c.parent).all()
        print(datetime.now()-dts, "TIME\n")

        pts = []
        for i in sibs:
            if(i[0] in idList and idList[i[0]] not in pts):
                pts.append(idList[i[0]])


        return gen_fListFig(db, test["userid"], pts)

    @app.callback(
        Output("histogram", "figure"),
        [Input("timeck", "value"),
        Input("dropdown", "value")],
        [State("fList", "figure")]
    )
    def update_histogram( times, ddvalue, figure):
        selection = figure["data"][0]["selectedpoints"]
        print("ddvalue:" , ddvalue)

        print(selection)

        selectedFiles = [namesList[x] for x in selection]
        selectedFiles.append(ddvalue)


        @cache.memoize()
        def dbquery(selection):
            dates_uf = None
            if(ddvalue == 'All'):
                #If all dates are wanted, query is different for more optimization
                dates_uf = sess.query(Dates.moddate).join(Files).filter(Files.parent_id==test["userid"]).all()
            else:
                dates_uf = sess.query(Dates.moddate).join(Files).filter(and_(Files.parent_id==test["userid"],
                    Files.fileName.in_(selectedFiles))).all()

            return dates_uf



        dates_uf = dbquery(selection)

        tickformat=""
        if(times):
            dates = [x[0].replace(year=2000, month = 1, day = 1) for x in dates_uf]
            tickformat="%H:%M"
        else:
            dates = [x[0] for x in dates_uf]

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
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def getoptions(value):
        return genOptList(test["userid"])

    '''
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
    '''



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

