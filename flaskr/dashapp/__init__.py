# -*- coding: utf-8 -*-
from flaskr.dashapp.dash_functions import *
import flask
from flask import current_app


pp = PrettyPrinter(indent=3)

def register_dashapp(flask_serv):
    from flaskr.dashapp.callbacks import register_callback, Loader
    from flaskr.dashapp.layout import return_layout
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    dashapp = dash.Dash(__name__, server = flask_serv,external_stylesheets=external_stylesheets, url_base_pathname = "/dash/")

    with flask_serv.app_context():
        Loader.setpdpath (flask_serv.config["HOMEDATAPATH"])

        dashapp.layout = return_layout()
        register_callback(dashapp)
