from processing.sql import reload_engine, func
from math import log
import plotly.graph_objects as go
from .dash_functions import gen_margin, idIndexMapper, namesList
from processing.models import Closure, Files, Dates, Filename
import flask


def _updateBubbleChart(_n_clicks, selection):
    # Returns a go.Figure with a bubble chart with all files and corresponding dates,
    # and a string for the parent of currently selected

    db = reload_engine(flask.session["userid"], download=True)

    #Should only be run at the beginning and when getting parents

    # Return selected point id
    selectedPointId = selection["points"][0]['customdata']

    selectionIndex, parentLabel = sibs_from_id(db, selectedPointId)

    fListFig = getNormalBubbleData(db)

    if (selectionIndex):
        # Set selectedpoints if there exists slPoints param
        fListFig["data"][0]["selectedpoints"] = selectionIndex

    return fListFig, parentLabel


def sibs_from_id(db, fileId: int):
    # Returns all sibling files as an array of fileIds
    # and the parentLabel

    # Subquery to get the fileId of the parent
    immediateParent = db.query(Closure.parent).filter(
        (Closure.depth == 1) & (Closure.child == fileId) &
        (Closure.owner_id == flask.session["userid"])).limit(1).subquery()

    try:
        # Query the subquery to get the filename
        parentLabel = db.query(Filename.fileName).join(
            immediateParent,
            Filename.fileId == immediateParent.c.parent).first()[0]
    except TypeError:
        parentLabel = "no parent"

    sibs = db.query(Files.id).join(Closure, Closure.child == Files.id) \
        .filter((Files.parent_id == flask.session["userid"]) &( Closure.parent == immediateParent.c.parent)) \
        .distinct().all()

    #Pts: array of indexes to select. Required by dash
    #idIndexMapper is a dict that maps filenames to indexes
    pts = set()
    for i in sibs:
        fileId = i.id

        if (fileId in idIndexMapper and idIndexMapper[fileId] not in pts):
            # Dash doesn't accept fileId as input to determine what points are currently selected.
            # Instead, it uses the index of the given list in the figure (go.Figure(x = ..., y = ...)) to
            # determine selection. Therefore, pts is not the fileId, but rather the corresponding index
            pts.append(idIndexMapper[fileId])

    return pts, parentLabel


def getNormalBubbleData(db):

    #Get all the files with their counts of edits and last modified time
    allFiles = db.query(Files.id, Dates.date.label('va')).join(Dates).subquery()

    #Group by id
    times = db.query(allFiles.c.id, func.sum(allFiles.c.va).label('count')) \
            .group_by(allFiles.c.id).subquery()

    #Join id to filename
    #per element in count: (filename, file.id, count, last mod date)
    #per elemnt in count: (id, count, filename, lastmoddate)
    result = db.query(times.c.id, times.c.count, Filename.fileName, Files.lastModDate) \
            .join(Filename, Filename.fileId == times.c.id) \
            .join(Files, Files.id == times.c.id).all()

    activity = {}
    activity["time"] = [x.lastModDate for x in result]
    activity["files"] = [x.fileName for x in result]
    activity["marker"] = [log(x.count, 6) for x in result]

    # When another function receives a callback for selected data,
    # it will also get the fileid allowing it to query DB as necessary
    activity["custom"] = [x.id for x in result]

    for counter, f in enumerate(activity["custom"]):
        # idIndexMapper indexes filename and corresponding index
        # namesList indexes index by corresponding filename
        # Used for quick references and changing current selection on graph
        idIndexMapper[f] = counter
        namesList[counter] = f

    return go.Figure(data=go.Scatter(
        y=activity["time"],
        x=activity["files"],
        mode="markers",
        marker_size=activity["marker"],
        selected={'marker': {
            'color': 'darkorange'
        }},
        customdata=activity["custom"]),
                     layout={
                         'clickmode': 'event+select',
                         'margin': gen_margin(),
                         'title': "BubbleChart",
                         'xaxis': {
                             'visible': False
                         }
                     })
