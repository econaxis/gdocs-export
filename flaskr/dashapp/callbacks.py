import time
import itertools
import dash
import logging
from processing.models import Dates, Files
from processing.sql import v_scoped_session 
from datetime import datetime
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from pprint import pformat, PrettyPrinter
from flaskr.dashapp.dash_functions import genOptList, gen_fListFig, gen_margin, idIndexMapper, namesList
import numpy as np
from processing.models import Closure, Dates, Files, Filename
from sqlalchemy import and_

pprint = PrettyPrinter(indent=4).pprint

logger = logging.getLogger(__name__)


print("logger: %s"%__name__)

db = v_scoped_session()

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

replace_values = {'foo'}


g_values = []
g_weights = []

def _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure ):


    ctx = dash.callback_context

    replace_existing = False



    #Check if button was triggerd
    #TODO

    for i in ctx.triggered:
        if i["prop_id"] == 'trace':
            replace_existing = False


    logger.debug("update_histogram called")

    #Testing
    time.sleep(3)

    selection = bubble_figure["data"][0].get("selectedpoints", [])
    selectedFiles = [namesList[x] for x in selection]
    selectedFiles += [x["customdata"] for x in selectedData["points"]]

    #Selected files is a list of file.ids 

    # Add current value in dropdown to selectedFiles for SQL query
    #TODO: check whether necessary?
    selectedFiles.append(ddvalue)

    logger.debug("file ids: %s", pformat(selectedFiles))

    #@cache.memoize()
    def dbquery(p_selectedFiles):
        # Returns list of all dates associated with particular selection
        # Parameter selectedFiles consists of lists of filenames

        if(ddvalue == 'All'):
            # If all dates are wanted, query is different for more
            # optimization
            dates_uf = db.query(Dates.bins, Dates.values).join(Files).filter(Files.parent_id == test["userid"]).all()
        else:
            # TODO: optimize query. fileName.in_ has to do long string
            # search
            dates_uf = db.query(Dates.bins, Dates.values).join(Files).filter(and_(Files.parent_id == test["userid"], \
                                         Files.id.in_(p_selectedFiles), Dates.isTime == False)).all()

        return dates_uf



    #Get list of Python datetime objects to compute histogram
    #datess_uf : List of tuples (bins (Int), values(Int))
    dates_uf = dbquery(selectedFiles)

    values = [None] * len(dates_uf)
    weights = [None] * len(dates_uf)


    for count, i in enumerate(dates_uf):
        #1 tuple of bin, value. Merge histogram by doing value = bin * weight
        values[count] = i[0]
        weights[count] = i[1]

    global g_values, g_weights

    g_values.append(values)
    g_weights.append(weights)

    bar_trace = []

    concat_weights = list(itertools.chain.from_iterable(g_weights))
    concat_values = list(itertools.chain.from_iterable(g_values))

    bin_edges = np.histogram_bin_edges(concat_values, bins = 40, weights = concat_weights)

    for values, weights in zip(g_values, g_weights):
        #histogram with timestamp instead of pydatetime for bins
        hist_1 = list(np.histogram(values, bins = bin_edges, weights = weights))
        hist_2  = [None, None]
        #Convert timestamp to pydatetime
        hist_2[1] = [datetime.fromtimestamp(float(x)) for x in hist_1[1]]
        hist_2[0] = [int(x) for x in hist_1[0]]

        bar_trace.append(go.Bar(x = hist_2[1], y = hist_2[0], opacity = 0.7))


    bar_trace = list(reversed(bar_trace))


    if replace_existing or True:
        hist_figure["data"] = bar_trace
    elif False:
        hist_figure["data"].append(bar_trace)

    if times:
        hist_figure["layout"]["xaxis"]["tickformat"] = "%H:%M"
    else:
        hist_figure["layout"]["xaxis"]["tickformat"] = ""


    return hist_figure


    '''
    if(times):
        # Times mode: set all the dates to be equal so Dash can make a
        # proper time histogram
        temp = [x.replace(year=2000, month=1, day=1) for x in hist_2[1]]
        hist_2[1] = temp
    '''



def _updateBubbleChart(_n_clicks, selection):

    if(_n_clicks == None or selection == None):
        return gen_fListFig(db, test["userid"], slPoints=pts), parentLabel
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
        Input("fList", "selectedData"),
        Input('trace', 'n_clicks')],
        [State('histogram', 'figure')]
    )
    def update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure):
        return _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure)

    @app.callback(
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def genDropdownOptions(value):
        return genOptList(test["userid"])


