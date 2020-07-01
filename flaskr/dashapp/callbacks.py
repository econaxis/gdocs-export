from types import SimpleNamespace
import threading
import logging
from processing.sql import reload_engine
from datetime import datetime
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from flaskr.dashapp.dash_functions import namesList
import flask
import numpy as np
from processing.models import Dates, Files

logger = logging.getLogger(__name__)

times_tickf = {
    'day': '%H:%M',
    'week': '%a %H:%M',
    'month': '%d',
    'year': '%m %d'
}

# Small, med, large preexisting values of DB
flask.session = dict(userid='med')

sessions_lock = threading.Lock()

sel_lock = threading.Lock()

logger.info("DASH CALLBACKS IMPORTED")
# Debug in place for flask.session

traces = []

prev_bins = []


early_ret = SimpleNamespace(adds=[],
                            deletes=[],
                            add_dates=[],
                            delete_dates=[])


def aggregate_dates(timestamps, aggregate_by):
    #Utility function to aggregate a list of timestamps by any value (month, year, week, ...)
    if aggregate_by == '':
        #No aggregate
        pass
    elif aggregate_by == 'day':
        timestamps = [
            datetime.fromtimestamp(x).replace(year=2000, month=1,
                                              day=1).timestamp()
            for x in timestamps
        ]
    elif aggregate_by == 'week':
        timestamps = [datetime.fromtimestamp(x) for x in timestamps]
        timestamps = [
            x.replace(year=2019, month=7, day=x.weekday() + 1).timestamp()
            for x in timestamps
        ]
    elif aggregate_by == 'month':
        timestamps = [
            datetime.fromtimestamp(x).replace(year=2000, month=1).timestamp()
            for x in timestamps
        ]
    elif aggregate_by == 'year':
        timestamps = [
            datetime.fromtimestamp(x).replace(year=2000).timestamp()
            for x in timestamps
        ]

    return timestamps


dir_lock = threading.Lock()


def query_db(files):

    logger.warning("query_db called")


    db = reload_engine(flask.session["userid"],
                       lock=sessions_lock)

    if files:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).join(Files) \
                .filter(Files.id.in_(files)).all()
    else:
        results = db.query(Dates.adds, Dates.deletes, Dates.date).all()

    return results


def get_activity(files=None,
                 x_limits=None,
                 aggregate_by='none',
                 filter_func=None,
                 use_prev_bins=True,
                 window=20,
                 num_bins=70):

    #Returns list of adds/deletes/corresponding dates as a namedtuple

    from scipy.stats import binned_statistic

    if use_prev_bins and len(prev_bins):
        # Use the previous bins (as a list) if we are allowed to.
        num_bins = prev_bins


    results = query_db(tuple(files) if files else None)

    adds = []
    deletes = []
    timestamps = []

    try:
        [adds1, deletes1, timestamps1] = map(list, zip(*results))
    except ValueError:
        logger.warning("cannot get results")
        return early_ret

    if filter_func:
        for c, i in enumerate(timestamps1):
            if filter_func(i):
                timestamps.append(timestamps1[c])
                adds.append(adds1[c])
                deletes.append(-1 * deletes1[c])

    if not timestamps:
        # No dates were returned in the filter_func
        return early_ret

    timestamps = aggregate_dates(timestamps=timestamps,
                                 aggregate_by=aggregate_by)

    [adds, deletes,
     timestamps] = list(map(np.array, [adds, deletes, timestamps]))

    add_dates = timestamps[:-1]
    delete_dates = timestamps[:-1]


    if not x_limits and aggregate_by == 'none':
        x_limits = [timestamps.min(), timestamps.max()]


    global prev_bins


    if x_limits:
        dbg_x = list(map(datetime.fromtimestamp, x_limits))
        print("DBG_X: ", dbg_x)

    adds, add_dates, bin_number = binned_statistic(
        timestamps,
        adds,
        'sum',
        #Only use previous bins if prev-bins exists and we are allowed to.
        #When overlaying various selections and adding, we need to have the same bin
        #configuration for plotly to work properly
        bins=num_bins,
        range=x_limits)

    deletes, delete_dates, bin_number = binned_statistic(
        timestamps,
        deletes,
        'sum',
        bins=num_bins,
        range=x_limits)

    np.insert(adds, 0, 0)
    np.insert(add_dates, 0, add_dates[0] - 1 * 24 * 3600)

    np.insert(deletes, 0, 0)
    np.insert(delete_dates, 0, delete_dates[0] - 1 * 24 * 3600)

    prev_bins = add_dates

    adds[1:] = apply_smoothing(adds[1:], min(len(adds), window))
    deletes[1:] = apply_smoothing(deletes[1:],
                                  min(len(deletes), window),
                                  negative=True)

    add_dates = [datetime.fromtimestamp(x) for x in add_dates]
    delete_dates = [datetime.fromtimestamp(x) for x in delete_dates]

    #Returns object with adds = magnitude character addition, add_dates = pydatetime with same shape as adds
    #Will get processed by calling function into appropriate go.Scatter objects
    return SimpleNamespace(adds=adds,
                           deletes=deletes,
                           add_dates=add_dates,
                           delete_dates=delete_dates)


def apply_smoothing(data, window, poly_order=3, negative=False):
    import scipy.signal
    window -= window % 2 + 1

    data = scipy.signal.savgol_filter(data, window, poly_order)

    if negative:
        data = [0 if x > 0 else x for x in data]
    else:
        data = [0 if x < 0 else x for x in data]
    return data


#Returns go Traces from selectedData ids, can be cumalative or no
def get_traces(times,
               ddvalue,
               bubble_figure,
               selectedData,
               trace,
               hist_figure,
               window_slider_value=30,
               bin_slider_value=40,
               x_limits=None,
               cumalative=False):

    logger.debug("updating histogram")

    if bubble_figure["data"][0]:
        selection = bubble_figure["data"][0].get("selectedpoints", [])
        selectedFiles = [namesList[x] for x in selection]
        selectedFiles.extend([x["customdata"] for x in selectedData["points"]])
    else:
        selectedFiles = []

    #Prepare selectedFiles (list of file ids in SQLite) to send to query_db
    selectedFiles.append(ddvalue)

    #Default value for adding new traces, always use the previous bins
    use_prev_bins = True

    #Times is variable with id timeck

    if times == 'none' or times == None:
        #Here, times must be 'none'
        tickformat = ""
        #Using previous bins to aggregate doesn't lead to good results, so we disable
        use_prev_bins = False
    else:
        tickformat = times_tickf[times]

    hist_figure["layout"]["xaxis"]["tickformat"] = tickformat

    #if we are generating a cumalative view, then we dont want to smoothen
    smoothing = not cumalative

    ret1 = get_activity(selectedFiles,
                        num_bins=bin_slider_value,
                        x_limits=x_limits,
                        window=window_slider_value,
                        aggregate_by=times,
                        use_prev_bins=use_prev_bins)

    if cumalative:
        #Further processing by cumalative sum
        ret1.adds = np.cumsum(ret1.adds)
        ret1.deletes = np.cumsum(ret1.deletes)

        ret1.adds = apply_smoothing(ret1.adds,
                                    min(len(ret1.adds), window_slider_value))
        ret1.deletes = apply_smoothing(ret1.deletes,
                                       min(len(ret1.deletes),
                                           window_slider_value),
                                       negative=True)

    add_trace1 = go.Scatter(x=ret1.add_dates,
                            y=ret1.adds,
                            mode='lines',
                            name='add',
                            stackgroup='add')
    delete_trace1 = go.Scatter(x=ret1.delete_dates,
                               y=ret1.deletes,
                               mode='lines',
                               name='delete',
                               stackgroup="delete")

    #Returns tuples of traces to add to figure["data"] property
    return add_trace1, delete_trace1, ret1


def register_callback(app):

    @app.callback(Output("sunburst", "figure"), [Input("url", "pathname")])
    def gen_sunburst(url):
        from flaskr.dashapp.sunburst import sunburst
        sunburst_figure = sunburst()
        logger.info(sunburst_figure)
        return sunburst_figure

    """

    @app.callback(
        [Output("fList", "figure"),
         Output("parent_span", "children")], [Input('get_parent', "n_clicks")],
        [State("fList", "selectedData")])
    def updateBubbleChart(_n_clicks, selection):
        return
        return _updateBubbleChart(_n_clicks, selection)

    @app.callback(Output("histogram", "figure"), [
        Input("timeck", "value"),
        Input("dropdown", "value"),
        Input("fList", "figure"),
        Input("fList", "selectedData"),
        Input('trace', 'n_clicks'),
        Input('bin-slider', 'value'),
        Input('histogram', 'relayoutData'),
        Input('window-slider', 'value')
    ], [State('histogram', 'figure')])
    def update_histogram(times, ddvalue, bubble_figure, selectedData, trace,
                         bin_slider, relayout, window_slider, hist_figure):
        return



        #Setting this to True disables creating new traces; we should only create new traces when bubble figure changes
        only_smoothen = True
        x_limits = None


        #When zoom is changed and we want to recalculate all traces, default behaviour
        #is to append traces if recalc_all is False (default)
        recalc_all = False

        ctx = dash.callback_context
        for i in ctx.triggered:
            logger.info("ctx.triggered: %s", i["prop_id"])

        global prev_bins
        for i in ctx.triggered:
            #TODO: fix
            prop_id = i["prop_id"]

            if prop_id == 'histogram.relayoutData':
                if "xaxis.range[0]" in relayout:
                    x_limits = [
                        datetime.strptime(relayout["xaxis.range[0]"], '%Y-%m-%d %H:%M:%S.%f').timestamp(),
                        datetime.strptime(relayout['xaxis.range[1]'], '%Y-%m-%d %H:%M:%S.%f').timestamp()
                    ]
                else:
                    #User reset zoom, data not available so we use default None value
                    x_limits = None

                recalc_all = True
                prev_bins = []
            elif prop_id == 'fList.selectedData': 
                #Only here can we add new traces
                only_smoothen = False
                hist_figure["layout"]["xaxis"]["autorange"]=True
                x_limits = None
            elif prop_id == 'trace':
                pass
            elif prop_id in {'bin-slider.value', 'window-slider.value'}:
                only_smoothen = True
                prev_bins = []
                recalc_all= True
            elif prop_id == 'timeck.value':
                #Aggregation method changed, reset prev_bins to recompute new bins
                hist_figure["data"] = []
                prev_bins = []
                hist_figure["layout"]["xaxis"]["autorange"]=True
                x_limits = None


        window_slider = round(window_slider)

        if recalc_all:
            for t in hist_figure["data"]:
                #TODO: when zooming in, then zoom out?



                selectedData = get_sel(t["meta"])
                add_trace, delete_trace, ds = get_traces(times, ddvalue, bubble_figure, selectedData, trace, hist_figure,
                                 bin_slider_value=bin_slider, window_slider_value=window_slider, x_limits=x_limits, cumalative = True)

                if t["stackgroup"] == "add":
                    t["x"] = add_trace["x"]
                    t["y"] = add_trace["y"]
                else:
                    t["x"] = delete_trace["x"]
                    t["y"] = delete_trace["y"]

            #hist_figure and data list is mutable so we can do this
            return hist_figure



        #Selected data is the main input, determines what files the trace outputs, we
        #save the selectedData list into a global list, so we can reference it later

        index = add_sel(selectedData)


        add_trace, delete_trace, ret1 = get_traces(times, ddvalue, bubble_figure, selectedData, trace, hist_figure,
                                 bin_slider_value=bin_slider, window_slider_value=window_slider, x_limits=x_limits, cumalative = True)
        #Fill each trace's meta property with the index of its storage location
        add_trace["meta"] = index
        delete_trace["meta"] = index

        if only_smoothen:
            #Replace the last two data with this new data, because we just want to update,
            #happens ONLY if the user changes just the bin_slider, window_slider values
            hist_figure["data"][-2:] = [add_trace, delete_trace]
        elif times in {'none', None}:
            #Reconstruct the graph and set these as new traces, when times is not defined,
            #Stack mode is not good with an unlimited time range 
            hist_figure["data"] = [add_trace, delete_trace]
        else:
            #Add two new traces, only if the aggregate by is defined 
            hist_figure["data"].extend([add_trace, delete_trace])



        logger.warning("times: %s", times);


        return hist_figure

    @app.callback([
        Output('year-all', 'figure'),
        Output('week-all', 'figure'),
        Output('day-all', 'figure')
    ], [Input("url", "pathname")], [
        State("year-all", 'figure'),
        State('week-all', 'figure'),
        State('day-all', 'figure')
    ])
    def get_all(_filler, year_fig, week_fig, day_fig):
        return

        logger.warning("getting yearly traces")

        #On loading, dash calls callbacks with None values. We want to filter this out to 
        #avoid duplicate calls to this function
        if not _filler:
            return year_fig, week_fig, day_fig

        years = list(range(2016, 2022))

        year_traces = []
        week_traces = []
        day_traces = []
        for y in years:
            logger.info("processing for year %d", y)
            edges = [
                datetime(y, 1, 1).timestamp(),
                datetime(y + 1, 1, 1).timestamp()
            ]

            year_num_bins = np.linspace(
                datetime(2000, 1, 1).timestamp(),
                datetime(2001, 1, 1).timestamp(), 140)
            week_num_bins = np.linspace(
                datetime(2019, 7, 1).timestamp(),
                datetime(2019, 7, 8).timestamp(), 120)

            day_num_bins = np.linspace(
                datetime(2000, 1, 1).timestamp(),
                datetime(2000, 1, 2).timestamp(), 90)

            year_data = get_activity(aggregate_by='year',
                                     filter_func=partial(
                                         betw, edges[0], edges[1]),
                                     num_bins=year_num_bins,
                                     use_prev_bins=False,
                                     window=25)

            week_data = get_activity(aggregate_by='week',
                                     filter_func=partial(
                                         betw, edges[0], edges[1]),
                                     num_bins=week_num_bins,
                                     use_prev_bins=False,
                                     window=12)

            day_data = get_activity(aggregate_by='day',
                                    filter_func=partial(
                                        betw, edges[0], edges[1]),
                                    num_bins=day_num_bins,
                                    use_prev_bins=False,
                                    window=8)

            _year_fig = go.Scatter(x=year_data.add_dates,
                                   y=year_data.adds,
                                   name=f'year {y}',
                                   stackgroup='a')
            _week_fig = go.Scatter(x=week_data.add_dates,
                                   y=week_data.adds,
                                   name=f'year {y}',
                                   stackgroup='b')

            _day_fig = go.Scatter(x=day_data.add_dates,
                                  y=day_data.adds,
                                  name=f'year {y}',
                                  stackgroup='c')

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
        prev_bins = []

        return year_fig, week_fig, day_fig

    @app.callback(Output("dropdown", "options"), [Input("url", "pathname")])
    def genDropdownOptions(value):
        return
        #Use this to download db from azure
        userid = flask.session["userid"]
        reload_engine(userid, lock = sessions_lock)

        logger.warning("done download db and crete connectoin")

        return genOptList(flask.session["userid"])

    """


def betw(_min, _max, val):
    if val >= _min and val <= _max:
        return True
    else:
        return False
