from sqlalchemy.orm import aliased
from processing.models import Dates, Files, Closure, Filename
from sqlalchemy.orm.exc import MultipleResultsFound
from processing.sql import reload_engine
import plotly.graph_objects as go
from sqlalchemy.sql import func
import flask
import logging

logger = logging.getLogger(__name__)


def sunburst():
    #Queries DB to get the parent of each file
    #Returns go.Figure with Sunburst component

    db = reload_engine(flask.session["userid"])

    #Generate two aliases of the model Filename
    fn1, fn2 = aliased(Filename), aliased(Filename)


    ds = db.query(Closure.depth.label('__d'), \
                fn1.fileName.label('fn1_name'), fn1.fileId.label('fn1_id') , \
                fn2.fileName.label('fn2_name'), fn2.fileId.label('fn2_id')) \
                .join(fn1, fn1.fileId == Closure.parent) \
                .join(fn2, fn2.fileId == Closure.child) \
                .filter(Closure.depth==1).subquery()

    sds = db.query(
        Files.id.label('f_id'),
        func.sum(Dates.adds).label('adds'),
        func.sum(Dates.deletes).label("deletes"),
        func.count(Dates.id).label('num_dates')).outerjoin(Dates) \
        .group_by(Files.id).subquery()

    res = db.query(ds, sds).join(sds, sds.c.f_id == ds.c.fn2_id).all()

    # Parents: id (as generated by SQL) of the parent folder
    # Children: id of the child document or folder
    # Values: Only applicable to children with documents, contains the sum of add, delete operations
    #   corresponds to the activity
    # Names: maps each id in the children list to their names

    parents = [x.fn1_id for x in res]
    children = [x.fn2_id for x in res]

    values = [
        x.num_dates * (x.adds + x.deletes) if x.adds and x.deletes else 0
        for x in res
    ]
    names = [x.fn2_name for x in res]

    try:
        root_id = db.query(
            Filename.fileId).filter(Filename.fileName == "root").one()[0]
    except MultipleResultsFound as e:
        #When running for real, disable raise e, and just return an empty figure
        logger.exception("Multiple results found for filename \"root\"")
        raise e
        return go.Figure()

    # Dash requires the "root" to have a parent of ""
    parents.append("")
    children.append(root_id)
    names.append("Root")
    values.append(0)

    assert all(x==len(names) for x in [len(values), len(children), len(parents)]), \
            f""" The arrays of names ,values, children, parents are not of equal length:
            names: {names}\n values: {values} \n children: {children} \n parents: {parents}\n """

    return go.Figure(data=
        [
        go.Sunburst(ids=children,
                    labels=names,
                    parents=parents,
                    values=values,
                    branchvalues='remainder')
        ],
        layout=dict(margin=dict(t=0, l=0, r=0, b=0)))
