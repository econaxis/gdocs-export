import dash_core_components as dcc
import dash_html_components as html
from flaskr.dashapp.dash_functions import *

def return_layout():

    return html.Div([
        html.Div([
            html.Div([
                dcc.Graph(
                    id="fList",
                ), dcc.Dropdown(
                    id="dropdown",
                    value="sumDates"
                )
                ], className = "six columns",
                style = {
                'margin': gen_margin(l = 20)
                }
            ),
            html.Div([
                dcc.Graph(
                    id = "histogram"
                ),
                html.Button(
                    "Reset Histogram",
                    id = "reset_histogram"
                )
            ], className = "six columns"),
        ], id = "primary"),
        html.Div(
            id = "csvdata", style = {'display': 'none'}
        ),
        html.Div(
            id = "zoomInfo", style = {'display': 'none'}
        ),
        dcc.Location(id = 'url', refresh = False),
        html.Div([
            dcc.Graph(
                id="lineWord"
            )
        ], className = "four columns",
        style={'display':'none'})

    ])

