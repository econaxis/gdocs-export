import dash
import dash_core_components as dcc
from processing.models import Owner, Files, Dates
from processing.sql import scoped_sess as db
from processing.sql import scoped_sess
from datetime import datetime
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
import pprint
from dash.dash import no_update
from flask import current_app
import flask
from flaskr.dashapp.dash_functions import *
from flaskr.flask_config import CONF, cache

from processing.sql import sess
from processing.models import Owner, Files, Dates, Closure

from sqlalchemy.orm import joinedload
from sqlalchemy import and_
import pprint


pprint = PrettyPrinter(indent=4).pprint


test = {}


def register_callback(app):
    @app.callback(
	[Output("fList", "figure"),
	Output("parent_span", "children")],
	[Input('get_parent', "n_clicks")],
	[State("fList", "selectedData")]
    )
    def updateBubbleChart(_n_clicks,selection):
	#Return selected point in fileName
	selectedPoint = selection["points"][0]['x']


	#Get subquery for immediate parent, returns folder name of immediate parent 
	#by searching for depth of 1 in closure table
	immediateParent = db.query(Closure.parent).filter(and_(Closure.depth ==1,
	    Closure.child==selectedPoint, Closure.owner_id==test["userid"])).limit(1).subquery()

	try:
	  immediateParentLabel = db.query(immediateParent.c.parent).first()[0]
	except TypeError:
	  immediateParentLabel = "no parent"

	print(immediateParentLabel)

	#Query all Files.fileName that has the same parent value in the Closure table
	#TODO: export sibs to cache a fileid list in case we want to construct a histogram, right now,
	#to construct a histogram with selection, we query by filename, which is inefficient full text search
	#using fileid would allow for quicker queries
	sibs = db.query(Files.fileName).join(Closure, Closure.child==Files.fileName) \
		.filter(and_(Files.parent_id==test["userid"], Closure.parent==immediateParent.c.parent)).all()

	#Pts: array of indexes to select. Required by dash
	#idList is a dict that maps filenames to indexes
	pts = []
	for i in sibs:
	    if(i[0] in idList and idList[i[0]] not in pts):
		pts.append(idList[i[0]])


	#Slpoints to indicate what points are being selected
	return gen_fListFig(db, test["userid"], slPoints = pts), immediateParentLabel



    @app.callback(
	Output("histogram", "figure"),
	[Input("timeck", "value"),
	Input("dropdown", "value")],
	[State("fList", "figure")]
    )
    def update_histogram( times, ddvalue, figure):
	selection = figure["data"][0]["selectedpoints"]
	selectedFiles = [namesList[x] for x in selection]

	#Add current value in dropdown to selectedFiles for SQL query
	selectedFiles.append(ddvalue)


	@cache.memoize()
	def dbquery(selection):
	    #Returns list of all dates associated with particular selection
	    #Parameter selection consists of lists of filenames
	    if(ddvalue == 'All'):
		#If all dates are wanted, query is different for more optimization
		dates_uf = sess.query(Dates.moddate).join(Files).filter(Files.parent_id==test["userid"]).all()
	    else:
		#TODO: optimize query. fileName.in_ has to do long string search
		dates_uf = sess.query(Dates.moddate).join(Files).filter(and_(Files.parent_id==test["userid"],
		    Files.fileName.in_(selectedFiles))).all()

	    return dates_uf

	dates_uf = dbquery(selection)

	if(times):
	    #Times mode: set all the dates to be equal so Dash can make a proper time histogram
	    dates = [x[0].replace(year=2000, month = 1, day = 1) for x in dates_uf]
	else:
	    dates = [x[0] for x in dates_uf]

	return go.Figure(
	    data = [go.Histogram(x=dates, nbinsx=60)],
	    layout= dict(
		margin=gen_margin(),
		xaxis = dict(
		    tickformat="%H:%M" if times else "",
		    type="date"
		)
	    )
	)


    @app.callback(
	Output("dropdown", "options"),
	[Input("url", "pathname")])
    def genDropdownOptions(value):
	return genOptList(test["userid"])

    '''
    @app.callback(
	Output("dropdown", "value"),
	[Input("fList", "hoverData"), Input("fList", "selectedData")])
    def update_from_click(hover, click):
	if(hover == None and click == None):
	    return None

	if(click != None):
	    return click["points"][0]["x"]
	else:
	    return hover["points"][0]["x"]
    '''



class Loader:
    pydocPath = None
    @classmethod
    def setpdpath (cls, _pydocPath):
	cls.pydocPath = _pydocPath

    @classmethod
    def loadcsv (cls, path):
	return pd.read_pickle(path + 'collapsedFiles_p.pickle')

    @classmethod
    def loadActivity (cls, path):
	return pd.read_pickle(path +  'activity.pickle')

    @classmethod
    def loadHists(cls, path):
	return pd.read_pickle( path + 'hists.pickle')

