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
                            )
                        )
                    )
                ),
                html.Button(
                    "Get parent",
                    id="get_parent"
                ),
                dcc.RadioItems(
                    id="timeck",
                    options=[
                        {'label': 'Time Only', 'value': 'day'},
                        {'label': 'Week Only', 'value': 'week'},
                        {'label': 'None', 'value': 'none'}
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
            dcc.Slider(
                id='bin-slider',
                min=0,
                max=500,
                step=1,
                value=30
            ),
            dcc.Slider(
                id='window-slider',
                min=4,
                max=60,
                step=0.1,
                value=15
        )], className="twelve columns",),
        dcc.Location(id='url', refresh=False),
    ])
