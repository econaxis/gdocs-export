import dash
import configlog
import time
import logging
import configlog
import dash_core_components as dcc
from processing.models import Owner, Files, Dates
from processing.sql import scoped_sess as db
from datetime import datetime
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
import pprint
from pprint import pformat
from dash.dash import no_update
from flask import current_app
import flask
from flaskr.dashapp.dash_functions import *
from flaskr.flask_config import CONF, cache
from processing.sql import sess
from processing.models import Owner, Files, Dates, Closure
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

pprint = PrettyPrinter(indent=4).pprint
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


print("logger: %s"%__name__)


logger.info("DASH CALLBACKS IMPORTED")


# Debug in place for flask.session
test = {}


"""

DEBUG FOR HISTOGRAM

ftable = Files.__table__
q = select([literal_column("floor((datediff(second, '2010-05-06 12:00:00', moddate)/1000)*1000").label("bins"), ftable.c.id]).select_from(dtable.join(ftable)).alias()
q1 = select([q.c.fl, func.count('*')]).select_from(q).group_by(q.c.fl).order_by(q.c.fl)
CONN.execute(q1)
"""


def _update_histogram(times, ddvalue, figure, selectedData):

    logger.debug("update_histogram called")

    #Testing
    time.sleep(3)

    selection = figure["data"][0].get("selectedpoints", [])
    selectedFiles = [namesList[x] for x in selection]
    selectedFiles += [x["customdata"] for x in selectedData["points"]]

    #Selected files is a list of file.ids 

    # Add current value in dropdown to selectedFiles for SQL query
    #TODO: check whether necessary?
    selectedFiles.append(ddvalue)

    #@cache.memoize()
    def dbquery(p_selectedFiles):
        # Returns list of all dates associated with particular selection
        # Parameter selectedFiles consists of lists of filenames

        if(ddvalue == 'All'):
            # If all dates are wanted, query is different for more
            # optimization
            dates_uf = sess.query(Dates.moddate).join(Files).filter( Files.parent_id == test["userid"]).all()
        else:
            # TODO: optimize query. fileName.in_ has to do long string
            # search
            dates_uf = sess.query(Dates.moddate).join(Files).filter(and_(Files.parent_id == test["userid"],
                                                                         Files.id.in_(p_selectedFiles))).all()

        return dates_uf


    #Get list of Python datetime objects to compute histogram
    dates_uf = dbquery(selectedFiles)

    if(times):
        # Times mode: set all the dates to be equal so Dash can make a
        # proper time histogram
        dates = [x[0].replace(year=2000, month=1, day=1) for x in dates_uf]
    else:
        dates = [x[0] for x in dates_uf]

    #Return final histogram figure

    return go.Figure(
        data=[go.Histogram(x=dates, nbinsx=75)],
        layout=dict(
            margin=gen_margin(),
            xaxis=dict(
                tickformat="%H:%M" if times else "",
                type="date"
            )
        )
    )


def _updateBubbleChart(_n_clicks, selection):
    #Should only be run at the beginning and when getting parents
    logger.debug('update bubble chart')

    print(selection, 'selection')
    # Return selected point in fileName
    selectedPointId = selection["points"][0]['customdata']
    print(selectedPointId, "selected point id")

    # Get subquery for immediate parent, returns folder name of immediate parent
    # by searching for depth of 1 in closure table
    immediateParent = db.query(Closure.parent).filter(and_(Closure.depth == 1,
               Closure.child == selectedPointId, Closure.owner_id == test["userid"])).limit(1).subquery()

    try:

        parentLabel = db.query(Filename.fileName).join(immediateParent,  \
                Filename.fileId == immediateParent.c.parent).first()[0]
    except TypeError:
        parentLabel = "no parent"


    # Query all Files.fileName that has the same parent value in the Closure table
    # TODO: export sibs to cache a fileid list in case we want to construct a histogram, right now,
    # to construct a histogram with selection, we query by filename, which is inefficient full text search
    # using fileid would allow for quicker queries
    sibs = db.query(Files.id).join(Closure, Closure.child == Files.id) \
        .filter(and_(Files.parent_id == test["userid"], Closure.parent == immediateParent.c.parent)).distinct().all()

    # Pts: array of indexes to select. Required by dash
    # idIndexMapper is a dict that maps filenames to indexes
    pts = []
    for i in sibs:
        id = i[0]
        if(id in idIndexMapper and idIndexMapper[id] not in pts):
            #Explanation: 
            #sibs: list of 1-tuples that contains fileid
            #idIndexMapper is a dictionary mapping fileid to index in plotly graph
            #The pts list is then passed to figure generator to generate a new figure with all
            #sibling points selected
            print(id, idIndexMapper[id])
            pts.append(idIndexMapper[id])

    # Slpoints to indicate what points are being selected

    return gen_fListFig(db, test["userid"], slPoints=pts), parentLabel



# Moved functions out of register_callback for profiling to work
def register_callback(app):
    @app.callback(
        [Output("fList", "figure"),
         Output("parent_span", "children")],
        [Input('get_parent', "n_clicks")],
        [State("fList", "selectedData")]
    )
    def updateBubbleChart(_n_clicks, selection):
        return _updateBubbleChart(_n_clicks, selection)
    @app.callback(
        Output("histogram", "figure"),
        [Input("timeck", "value"),
         Input("dropdown", "value"),
        Input("fList", "figure"),
        Input("fList", "selectedData")]
    )
    def update_histogram(times, ddvalue, figure, selectedData):
        return _update_histogram(times, ddvalue, figure, selectedData)

    @app.callback(
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def genDropdownOptions(value):
        return genOptList(test["userid"])

