import dash_core_components as dcc
import dash
import plotly.graph_objects as go
import dash_html_components as html
from flaskr.dashapp.dash_functions import gen_fListFig, gen_margin
from flaskr.dashapp.callbacks import test
import flask


def layout():

    return html.Div([
        html.Div([
            html.Div([dcc.Graph(id="fList"),
                      dcc.Dropdown(id="dropdown")],
                     className="six columns",
                     style={'margin': gen_margin()}),
            html.Div([
                dcc.Graph(id="histogram",
                          figure=go.Figure(layout=dict(
                              margin=gen_margin(), xaxis=dict(type="date")))),
                html.Button("Get parent", id="get_parent"),
                dcc.RadioItems(id="timeck",
                               options=[{
                                   'label': 'Time Only',
                                   'value': 'day'
                               }, {
                                   'label': 'Week Only',
                                   'value': 'week'
                               }, {
                                   'label': 'None',
                                   'value': 'none'
                               }, {
                                   'label': 'Month',
                                   'value': 'month'
                               }]),
                html.Button("Save trace", id="trace")
            ],
                     className="six columns"),
        ],
                 id="primary"),
        html.Span(id="parent_span"),
        html.Div(
            [
                dcc.Slider(id='bin-slider', min=0, max=600, step=1, value=30),
                dcc.Slider(
                    id='window-slider', min=4, max=60, step=0.1, value=15)
            ],
            className="twelve columns",
        ),
        html.Header(children="""
            <!-- Global site tag (gtag.js) - Google Analytics -->
            <script async src="https://www.googletagmanager.com/gtag/js?id=UA-104236791-2"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());

              gtag('config', 'UA-104236791-2');
            </script>
            """),
        dcc.Location(id='url', refresh=False),
        html.Div([
            dcc.Graph(
                id="year-all",
                figure=go.Figure(
                    layout=dict(margin=gen_margin(), xaxis=dict(
                        type="date")))),
            dcc.Graph(
                id="week-all",
                figure=go.Figure(
                    layout=dict(margin=gen_margin(), xaxis=dict(
                        type="date")))),
            dcc.Graph(
                id="day-all",
                figure=go.Figure(
                    layout=dict(margin=gen_margin(), xaxis=dict(type="date"))))
        ],
                 className='twelve columns')
    ])
