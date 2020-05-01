import time
import pickle
import itertools
import dash
import logging
from processing.models import Dates, Files
from processing.sql import v_scoped_session 
from datetime import datetime, timezone
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from pprint import pformat, PrettyPrinter
from flaskr.dashapp.dash_functions import genOptList, gen_fListFig, gen_margin, idIndexMapper, namesList
import numpy as np
from scipy.stats import binned_statistic
import scipy.signal
from scipy import interpolate
from processing.models import Closure, Dates, Files, Filename, Owner
from sqlalchemy import and_

from collections import namedtuple



pprint = PrettyPrinter(indent=4).pprint

logger = logging.getLogger(__name__)


print("logger: %s"%__name__)

db = v_scoped_session()

logger.info("DASH CALLBACKS IMPORTED")


# Debug in place for flask.session
test = {}

trace_map = {}

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


def get_activity(files, smooth = False, window = 51, num_bins = 30, x_limits = [0, 2e9], aggregate_by = ''):


    if files:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).join(Files).join(Owner, Owner.id == Files.parent_id) \
                .filter(and_(Files.id.in_(files), Owner.id == test["userid"])).all()
    else:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).join(Files).join(Owner, Owner.id == Files.parent_id) \
                .filter(Owner.id==test["userid"]).all()



    adds = []
    deletes_abs = []
    timestamps = []

    [adds, deletes, timestamps] = zip(*results)


    if aggregate_by == '':
        #No aggregate
        pass
    elif aggregate_by == 'day':
        timestamps = [datetime.fromtimestamp(x).replace(year=2000, month = 1, day = 1).timestamp() for x in timestamps]
    elif aggregate_by == 'week':
        timestamps = [datetime.fromtimestamp(x) for x in timestamps]
        timestamps = [x.replace(year=2019, month=7, day=x.weekday()+1).timestamp() for x in timestamps]

    deletes = [-1 * x for x in deletes]

    adds = np.array(adds)
    deletes = np.array(deletes)
    timestamps = np.array(timestamps)
    add_dates = timestamps
    delete_dates = timestamps


    x_limits[0] = max(timestamps.min(), x_limits[0])
    x_limits[1] = min(timestamps.max(), x_limits[1])


    adds, add_dates, bin_number = map(list, binned_statistic(timestamps, adds, 'sum', bins=num_bins, range=x_limits))
    deletes, delete_dates, bin_number = map(list, binned_statistic(timestamps, deletes, 'sum', bins=num_bins, range = x_limits))

    add_dates = add_dates[:-1]
    delete_dates = delete_dates[:-1]

    if smooth:
        print(len(deletes), len(delete_dates))
        add_dates1 = np.linspace(min(add_dates), max(add_dates), 50)
        delete_dates1 = np.linspace(min(delete_dates), max(delete_dates), 50)

        #adds = interpolate.interp1d(add_dates, adds, kind='cubic')(add_dates1)
        #deletes = interpolate.interp1d(delete_dates, deletes, kind='cubic')(delete_dates1)
        #add_dates = add_dates1
        #delete_dates = delete_dates1



        #adds = np.interp(np.linspace(add_dates[0], add_dates[-1], 50), add_dates, adds)
        #deletes = np.interp(np.linspace(delete_dates[0], delete_dates[-1], 50), delete_dates, deletes)


        poly_order = 3

        window = min(window, len(adds), len(deletes))
        window = max(window, poly_order + 3)

        window -= window%2 + 1


        adds = scipy.signal.savgol_filter(adds, window, poly_order)
        deletes = scipy.signal.savgol_filter(deletes, window, poly_order)

        adds = [0 if x < 0 else x for x in adds]
        deletes = [0 if x > 0 else x for x in deletes]

    add_dates = [datetime.fromtimestamp(x) for x in add_dates]
    delete_dates = [datetime.fromtimestamp(x) for x in delete_dates]


    from types import SimpleNamespace

    return SimpleNamespace(adds = adds, deletes = deletes, add_dates = add_dates, delete_dates = delete_dates)

def _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure,
        window_slider_value = 30,bin_slider_value = 40, x_limits = [0, 2e9]):

    pickle.dump(hist_figure, open('figure', 'wb'))

    ctx = dash.callback_context

    replace_existing = False

    #Check if button was triggerd
    #TODO

    for i in ctx.triggered:
        if i["prop_id"] == 'trace':
            replace_existing = False


    logger.debug("update_histogram called")

    selection = bubble_figure["data"][0].get("selectedpoints", [])
    selectedFiles = [namesList[x] for x in selection]
    selectedFiles += [x["customdata"] for x in selectedData["points"]]

    #Selected files is a list of file.ids 

    # Add current value in dropdown to selectedFiles for SQL query
    #TODO: check whether necessary?
    selectedFiles.append(ddvalue)

    logger.debug("file ids: %s", pformat(selectedFiles))


    #Get list of Python datetime objects to compute histogram
    #datess_uf : List of tuples (bins (Int), values(Int))

    logger.info("window_slider_value: %d", window_slider_value)

    aggregate_by = ""
    tickformat = ""

    if times:
        tickformat = "%H:%M"
        aggregate_by = 'day'

    ret = get_activity(selectedFiles, num_bins = bin_slider_value, x_limits = x_limits, 
            window = window_slider_value, aggregate_by = aggregate_by)

    ret1 = get_activity(selectedFiles, smooth = True, num_bins = bin_slider_value, 
            x_limits = x_limits, window = window_slider_value, aggregate_by = aggregate_by)

    trace_map['add-nosmooth'] = dict(x = ret.add_dates, y = ret.adds)
    trace_map['delete-nosmooth'] = dict(x=ret.delete_dates, y=ret.deletes)
    trace_map['add-yessmooth'] = dict(x=ret1.add_dates, y = ret1.adds)
    trace_map['delete-yessmooth'] = dict(x=ret1.delete_dates, y = ret1.deletes)

    if hist_figure["data"]:
        for t in hist_figure["data"]:
            t['x'] = trace_map[t['meta']]['x']
            t['y'] = trace_map[t['meta']]['y']
    else:
        add_trace = go.Scatter(x = ret.add_dates, y = ret.adds, mode='lines', name='no smooth', meta = "add-nosmooth")
        delete_trace = go.Scatter(x = ret.delete_dates, y = ret.deletes, mode='lines', name='no smooth', meta = "delete-nosmooth")

        add_trace1 = go.Scatter(x = ret1.add_dates, y = ret1.adds, mode='lines', name='yes smooth', meta = "add-yessmooth")
        delete_trace1 = go.Scatter(x = ret1.delete_dates, y = ret1.deletes, mode='lines', name='yes smooth', meta = "delete-yessmooth")

        hist_figure["data"] = [add_trace, delete_trace, add_trace1, delete_trace1]

    hist_figure["layout"]["xaxis"]["tickformat"] = tickformat

    return hist_figure


    for count, i in enumerate(dates_uf):
        #1 tuple of bin, value. Merge histogram by doing value = bin * weight
        values[count] = i[0]
        weights[count] = i[1]


    global traces

    bin_edges = np.histogram_bin_edges(concat_values, bins = 90, weights = concat_weights)


    #histogram with timestamp instead of pydatetime for bins
    hist_1 = list(np.histogram(values, bins = bin_edges, weights = weights))
    hist_2  = [None, None]
    #Convert timestamp to pydatetime
    #Hist_2 is main hist, hist_1 is temporary
    hist_2[1] = [datetime.fromtimestamp(float(x)) for x in hist_1[1]]
    hist_2[0] = [int(x) for x in hist_1[0]]

    bar_trace.append(go.Bar(x = hist_2[1], y = hist_2[0], opacity = 0.7))


    bar_trace = list(reversed(bar_trace))



    global g_values, g_weights

    g_values.append(values)
    g_weights.append(weights)

    bar_trace = []

    concat_weights = list(itertools.chain.from_iterable(g_weights))
    concat_values = list(itertools.chain.from_iterable(g_values))




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
        Input('trace', 'n_clicks'),
        Input('bin-slider', 'value'),
        Input('histogram', 'relayoutData'),
        Input('window-slider', 'value')],
        [State('histogram', 'figure')]
    )
    def update_histogram(times, ddvalue, bubble_figure, selectedData, trace, bin_slider, relayout, window_slider, hist_figure):


        b = '1980-03-27 23:54:15.5691'
        e = '2030-03-27 23:54:15.5691'


        x_axis = [relayout.get("xaxis.range[0]", b),
            relayout.get('xaxis.range[1]', e)]

        logger.info(x_axis)
        x_axis = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').timestamp() for x in x_axis]

        logger.info(x_axis)

        print("window slider: ", window_slider)

        window_slider = round (window_slider)

       # x_axis = list(map(iso8601.parse_date, x_axis))

       # logger.info(list(map(datetime.isoformat, x_axis)))
       # x_axis = list(map(datetime.timestamp, x_axis))

        return _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure, bin_slider_value = bin_slider,
                window_slider_value = window_slider, x_limits = x_axis)

    @app.callback(
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def genDropdownOptions(value):
        return genOptList(test["userid"])


