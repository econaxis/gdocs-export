"""
TODO: 
    Data table to filter and add traces, view historical traces.
    Y-agregation. Aggregate by x-axis with dates/year/month, but y-aggregation by splitting by file, folder, parent, 
    Cumalative mode, when we want to track word count instead of activity.
    Change all paths to safejoin
"""

import os
import dash
from pprint import PrettyPrinter

pp = PrettyPrinter(indent=3)


def register_dashapp(flask_serv):
    from flaskr.dashapp.callbacks import register_callback
    from flaskr.dashapp.layout import layout
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    if "FLASKDBG" in os.environ and False:
        dashapp = dash.Dash(__name__,
                            external_stylesheets=external_stylesheets,
                            url_base_pathname="/dash/")
    else:
        dashapp = dash.Dash(__name__,
                            server=flask_serv,
                            external_stylesheets=external_stylesheets,
                            url_base_pathname="/dash/")

    with flask_serv.app_context():
        dashapp.layout = layout()
        register_callback(dashapp)
    """
    # Useful for hosting as an iframe, sets headers to allow origin to be *
    @dashapp.server.after_request
    def add_header(response):
        print("setting response headers!")
        #response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers[
            'Content-Security-Policy'] = 'frame-src * data: blob: ;'
        return response

    """

    if "FLASKDBG" in os.environ:

        #Calls run server immediately, so the thread blocks.
        #If we return normally (flaskdbg NOT in os.environ) then the parent caller
        #will call flask_serv.run
        print("starting run server")
        dashapp.run_server(debug=True, threaded=False, processes=1)


if __name__ == "__main__":
    register_dashapp(None)
