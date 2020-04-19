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
            ], className="six columns",
                style={
                'margin': gen_margin()
            }
            ),
            html.Div([
                dcc.Graph(
                    id="histogram"
                ),
                html.Button(
                    "Get parent",
                    id="get_parent"
                ),
                dcc.Checklist(
                    id="timeck",
                    options=[
                        {'label': 'Time Only', 'value': 'time'}
                    ]
                )
            ], className="six columns"),
        ], id="primary"),
        html.Span(
            id="parent_span"
        ),
        html.Div([
            dcc.Graph(
                id="lineWord"
            )
        ], className="four columns",
            style={'display': 'none'}),
        dcc.Location(id='url', refresh=False),

    ])
