# -*- coding: utf-8 -*-
from flaskr.dashapp.dash_functions import *
import flask
from flask import current_app


pp = PrettyPrinter(indent=3)

def register_dashapp(flask_serv):
    from flaskr.dashapp.callbacks import register_callback, Loader
    from flaskr.dashapp.layout import layout
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    #dashapp = dash.Dash(__name__, server = flask_serv,external_stylesheets=external_stylesheets, url_base_pathname = "/dash/")

    dashapp = dash.Dash(__name__,external_stylesheets=external_stylesheets, url_base_pathname = "/dash/")

    if flask_serv == None:
        flask_serv = dashapp.server

    with flask_serv.app_context():
        Loader.setpdpath (flask_serv.config["HOMEDATAPATH"])
        dashapp.layout = layout()
        register_callback(dashapp)
        dashapp.run_server(debug=True)

