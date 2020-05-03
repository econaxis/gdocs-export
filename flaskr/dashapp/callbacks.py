import time
from types import SimpleNamespace
import pickle
import itertools
from functools import partial
import dash
import logging
from processing.models import Dates, Files
from processing.sql import reload_engine 
from datetime import datetime, timezone
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from pprint import pformat, PrettyPrinter
from flaskr.dashapp.dash_functions import genOptList, gen_fListFig, gen_margin, idIndexMapper, namesList
import flask
import numpy as np
from scipy.stats import binned_statistic
import scipy.signal
from scipy import interpolate
from processing.models import Closure, Dates, Files, Filename
from sqlalchemy import and_

from collections import namedtuple



pprint = PrettyPrinter(indent=4).pprint

logger = logging.getLogger(__name__)

logger.info("DASH CALLBACKS IMPORTED")


# Debug in place for flask.session
test = {}

trace_map = {}

g_values = []
g_weights = []

traces = []

prev_bins = None

prev_trace = [[], []]

from functools import lru_cache

@lru_cache(maxsize = 10)
def query_db(files):
    db = reload_engine(flask.session["userid"])()

    print("calculating db")
    if files:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).join(Files) \
                .filter(Files.id.in_(files)).all()
    else:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).all()

    return results

def get_activity(files = None, smooth = True, window = 20, num_bins = 70, x_limits = [0, 2e9], aggregate_by = '', filter_func = bool,
        use_prev_bins = True):

    results = query_db (tuple(files) if files else None)

    adds = []
    deletes= []
    timestamps = []

    [adds1, deletes1, timestamps1] = map(list, zip(*results))

    for c, i in enumerate(timestamps1):
        if filter_func(i):
            timestamps.append(timestamps1[c])
            adds.append(adds1[c])
            deletes.append(-1 * deletes1[c])

    if not timestamps:
        print("early exit")
        return SimpleNamespace(adds = [], deletes = [], add_dates = [], delete_dates = [])


    if aggregate_by == '':
        #No aggregate
        pass
    elif aggregate_by == 'day':
        timestamps = [datetime.fromtimestamp(x).replace(year=2000, month = 1, day = 1).timestamp() for x in timestamps]
        x_limits = [0, 3e9]
    elif aggregate_by == 'week':
        timestamps = [datetime.fromtimestamp(x) for x in timestamps]
        timestamps = [x.replace(year=2019, month=7, day=x.weekday()+1).timestamp() for x in timestamps]
        x_limits = [0, 3e9]
    elif aggregate_by == 'month':
        timestamps = [datetime.fromtimestamp(x).replace(year=2000, month = 1).timestamp() for x in timestamps]
        x_limits = [0, 3e9]
    elif aggregate_by == 'year':
        timestamps = [datetime.fromtimestamp(x).replace(year=2000).timestamp() for x in timestamps]
        x_limits = [0, 3e9]


    adds = np.array(adds)
    deletes = np.array(deletes)
    timestamps = np.array(timestamps)
    add_dates = timestamps[:-1]
    delete_dates = timestamps[:-1]

    print("x_limits, ", x_limits)

    x_limits[0] = max(timestamps.min(), x_limits[0])
    x_limits[1] = min(timestamps.max(), x_limits[1])

    global prev_bins

    """
    if use_prev_bins and prev_bins:
        #Previous bins existing and we are allowed to use, but don't know if range fits?
        step_size = prev_bins[1] - prev_bins[0] #Only if prev_bin length > 2
        num_bins = np.arange(x_limits[0], x_limits[1], step_size)
        print("num_bins, step_size: ",num_bins, step_size)
    """


    adds, add_dates, bin_number = map(list, binned_statistic(timestamps, adds, 'sum',
        bins = num_bins ,range = x_limits))

    deletes, delete_dates, bin_number = map(list, binned_statistic(timestamps, deletes, 'sum',
        bins = num_bins , range = x_limits))

    prev_bins = add_dates
    #deletes, delete_dates, bin_number = map(list, binned_statistic(timestamps, deletes, 'sum', bins=num_bins, range = x_limits))


    if smooth:
        #adds = interpolate.interp1d(add_dates, adds, kind='cubic')(add_dates1)
        #deletes = interpolate.interp1d(delete_dates, deletes, kind='cubic')(delete_dates1)
        #add_dates = add_dates1
        #delete_dates = delete_dates1
        #adds = np.interp(np.linspace(add_dates[0], add_dates[-1], 50), add_dates, adds)
        #deletes = np.interp(np.linspace(delete_dates[0], delete_dates[-1], 50), delete_dates, deletes)

        poly_order = 3

        window = min(window, len(adds), len(deletes))
        window -= window%2 + 1

        adds = scipy.signal.savgol_filter(adds, window, poly_order)
        deletes = scipy.signal.savgol_filter(deletes, window, poly_order)

        adds = [0 if x < 0 else x for x in adds]
        deletes = [0 if x > 0 else x for x in deletes]


    add_dates = [datetime.fromtimestamp(x) for x in add_dates]
    delete_dates = [datetime.fromtimestamp(x) for x in delete_dates]


    return SimpleNamespace(adds = adds, deletes = deletes, add_dates = add_dates, delete_dates = delete_dates)

def _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure,
        window_slider_value = 30,bin_slider_value = 40, x_limits = [0, 2e9]):
    ctx = dash.callback_context

    replace_existing = False

    only_smoothen = False

    for i in ctx.triggered:
        #TODO: fix
        if i["prop_id"] == 'histogram.relayoutData':
            return hist_figure
        if i["prop_id"] == 'trace':
            replace_existing = False
        if i["prop_id"] in {'bin-slider.value', 'window-slider.value'}:
            only_smoothen=True
        if i["prop_id"] == 'timeck.value':
            global prev_bins
            hist_figure["data"] = []
            prev_bins = None


    logger.debug("update_histogram called")
    if bubble_figure["data"][0]:
        selection = bubble_figure["data"][0].get("selectedpoints", [])
    else:
        selection = []

    selectedFiles = [namesList[x] for x in selection]
    selectedFiles += [x["customdata"] for x in selectedData["points"]]

    #Selected files is a list of file.ids 

    # Add current value in dropdown to selectedFiles for SQL query
    #TODO: check whether necessary?
    selectedFiles.append(ddvalue)

    #Get list of Python datetime objects to compute histogram
    #datess_uf : List of tuples (bins (Int), values(Int))

    aggregate_by = ""
    tickformat = ""

    if times == 'day':
        tickformat = "%H:%M"
        aggregate_by = 'day'
    elif times == 'week':
        tickformat = "%a %H:%M"
        aggregate_by = 'week'
    elif times=='month':
        aggregate_by = 'month'
        tickformat = '%d'
    elif times=='year':
        aggregate_by='year'
        tickformat='%m %d'


    ret1 = get_activity(selectedFiles, smooth = True, num_bins = bin_slider_value,
            x_limits = x_limits, window = window_slider_value, aggregate_by = aggregate_by)

    add_trace1 = go.Scatter(x = ret1.add_dates, y = ret1.adds, mode='lines', name='add', meta = "add-yessmooth", stackgroup = 'a')
    delete_trace1 = go.Scatter(x = ret1.delete_dates, y = ret1.deletes, mode='lines', name='delete', meta = "delete-yessmooth", stackgroup = "b")

    if only_smoothen:
        hist_figure["data"][-2:] = [add_trace1, delete_trace1]
    elif aggregate_by != '':
        hist_figure["data"].extend([add_trace1, delete_trace1])
    else:
        hist_figure["data"] = add_trace1, delete_trace1


    #hist_figure["data"].extend([add_trace1, delete_trace1])

    hist_figure["layout"]["xaxis"]["tickformat"] = tickformat

    return hist_figure

    """


    #Following is deprecated 


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


    """


def _updateBubbleChart(_n_clicks, selection):

    db = reload_engine(flask.session["userid"])
    parentLabel = ""

    #Should only be run at the beginning and when getting parents

    # Return selected point in fileName
    #selectedPointId = selection["points"][0]['customdata']

    # Get subquery for immediate parent, returns folder name of immediate parent
    # by searching for depth of 1 in closure table
    #immediateParent = db.query(Closure.parent).filter(and_(Closure.depth == 1,
               #Closure.child == selectedPointId, Closure.owner_id == test["userid"])).limit(1).subquery()
    #try:
        #parentLabel = db.query(Filename.fileName).join(immediateParent,  \
                #Filename.fileId == immediateParent.c.parent).first()[0]
    #except TypeError:
        #parentLabel = "no parent"


    # Query all Files.fileName that has the same parent value in the Closure table
    # TODO: export sibs to cache a fileid list in case we want to construct a histogram, right now,
    # to construct a histogram with selection, we query by filename, which is inefficient full text search
    # using fileid would allow for quicker queries
    #sibs = db.query(Files.id).join(Closure, Closure.child == Files.id) \
        #.filter(and_(Files.parent_id == test["userid"], Closure.parent == immediateParent.c.parent)).distinct().all()

    # Pts: array of indexes to select. Required by dash
    # idIndexMapper is a dict that maps filenames to indexes
    pts = []
    #for i in sibs:
        #id = i[0]
        #if(id in idIndexMapper and idIndexMapper[id] not in pts):
            #Explanation: 
            #sibs: list of 1-tuples that contains fileid
            #idIndexMapper is a dictionary mapping fileid to index in plotly graph
            #The pts list is then passed to figure generator to generate a new figure with all
            #sibling points selected
            #pts.append(idIndexMapper[id])

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

        if relayout:
            x_axis = [relayout.get("xaxis.range[0]", b),
                relayout.get('xaxis.range[1]', e)]
        else:
            x_axis = [b, e]

        x_axis = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').timestamp() for x in x_axis]

        window_slider = round (window_slider)

       # x_axis = list(map(iso8601.parse_date, x_axis))

       # logger.info(list(map(datetime.isoformat, x_axis)))
       # x_axis = list(map(datetime.timestamp, x_axis))

        return _update_histogram(times, ddvalue, bubble_figure, selectedData, trace, hist_figure, bin_slider_value = bin_slider,
                window_slider_value = window_slider, x_limits = x_axis)

    @app.callback(
        [Output('year-all', 'figure'),
        Output('week-all', 'figure'),
        Output('day-all', 'figure')],
        [Input("url", "pathname")],
        [State("year-all", 'figure'),
        State('week-all', 'figure'),
        State('day-all', 'figure')])
    def get_all(_filler, year_fig, week_fig, day_fig):

        if not _filler:
            return year_fig, week_fig, day_fig

        years = list(range(2016, 2021))

        year_traces = []
        week_traces = []
        day_traces = []
        for y in years:
            edges = [datetime(y, 1, 1).timestamp(), datetime(y+1, 1, 1).timestamp()]


            year_num_bins = np.linspace(datetime(2000, 1, 1).timestamp(), datetime(2001, 1, 1).timestamp(), 260)
            week_num_bins = np.linspace(datetime(2019, 7, 1).timestamp(), datetime(2019, 7, 8).timestamp(), 500)

            day_num_bins = np.linspace(datetime(2000, 1, 1).timestamp(), datetime(2000, 1, 2).timestamp(), 120)

            year_data = get_activity (aggregate_by = 'year', filter_func = partial(betw, edges[0], edges[1]),
                    num_bins = year_num_bins, use_prev_bins = False, window = 9)

            week_data = get_activity (aggregate_by = 'week', filter_func = partial(betw, edges[0], edges[1]),
                    num_bins = week_num_bins, use_prev_bins = False, window = 9)

            day_data = get_activity (aggregate_by = 'day', filter_func = partial(betw, edges[0], edges[1]),
                    num_bins = day_num_bins, use_prev_bins = False, window = 12)


            _year_fig = go.Scatter(x = year_data.add_dates, y = year_data.adds, name = f'year {y}', stackgroup = 'a')
            _week_fig = go.Scatter(x = week_data.add_dates, y = week_data.adds, name = f'year {y}', stackgroup = 'b')

            _day_fig = go.Scatter(x = day_data.add_dates, y = day_data.adds, name = f'year {y}', stackgroup = 'c')


            year_traces.append(_year_fig)
            week_traces.append(_week_fig)
            day_traces.append(_day_fig)

        year_fig["data"] = year_traces
        week_fig["data"] = week_traces
        day_fig["data"] = day_traces

        week_fig["layout"]["xaxis"]["tickformat"] = "%a %H:%M"
        day_fig["layout"]["xaxis"]["tickformat"] = "%a %H:%M"
        year_fig["layout"]["xaxis"]["tickformat"] = "%B %d"


        global prev_bins
        prev_bins = None


        return year_fig, week_fig, day_fig




    @app.callback(
        Output("dropdown", "options"),
        [Input("url", "pathname")])
    def genDropdownOptions(value):
        if value == None:
            return
        return genOptList(test["userid"])



counter = 0
def betw(_min, _max, val):

    m, mm, v = list(map(datetime.fromtimestamp, [_min, _max, val]))

    if val >= _min and val <= _max:
        return True
    else:
        return False
