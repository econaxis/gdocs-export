import dash_core_components as dcc
import dash
import plotly.graph_objects as go
import dash_html_components as html
from flaskr.dashapp.dash_functions import gen_fListFig, gen_margin
from processing.sql import v_scoped_session
from flaskr.dashapp.callbacks import test

scoped_sess = v_scoped_session()


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
                    id="histogram",
                    figure = go.Figure(
                        layout=dict(
                            margin=gen_margin(),
                            xaxis=dict(
                                type="date"
                            ),
                            barmode = 'overlay'
                        )
                    )
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
                ),
                html.Button(
                    "Save trace",
                    id = "trace"
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
