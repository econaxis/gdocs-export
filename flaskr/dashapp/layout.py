import dash_core_components as dcc
import dash_html_components as html
from flaskr.dashapp.dash_functions import *
from processing.sql import scoped_sess
from flaskr.dashapp.callbacks import test

def layout():
    return html.Div([
        html.Div([
            html.Div([
                dcc.Graph(
                    id="fList",
                    figure=gen_fListFig(scoped_sess, test["userid"])
                ), dcc.Dropdown(
                    id="dropdown"
                )
                ], className = "six columns",
                style = {
                'margin': gen_margin()
                }
            ),
            html.Div([
                dcc.Graph(
                    id = "histogram"
                ),
                html.Button(
                    "Reset Histogram",
                    id = "reset_histogram"
                ),
                dcc.Checklist(
                    id="timeck",
                    options=[
                        {'label': 'Time Only', 'value': 'time'}
                    ]
                )
            ], className = "six columns"),
        ], id = "primary"),
        dcc.Location(id = 'url', refresh = False),
        html.Div([
            dcc.Graph(
                id="lineWord"
            )
        ], className = "four columns",
        style={'display':'none'})

    ])

