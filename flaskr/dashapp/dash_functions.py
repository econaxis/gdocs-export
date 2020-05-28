# For use with dash app.py
import flask
from pprint import PrettyPrinter
from processing.models import Files, Filename
from processing.sql import reload_engine

import logging

logger = logging.getLogger(__name__)

#Maps fileid to index, TODO: global variable fix
idIndexMapper = {}

#maps index to fileid
namesList = [None] * 5000

pprint = PrettyPrinter(indent=4).pprint


##@cache.memoize()
def genOptList(userid):

    logger.info("userid: %s", flask.session["userid"])
    db = reload_engine(userid)()
    #Get list of all filenames and fileids by owner id

    names = db.query(Files.id, Filename.fileName).join(Filename).all()

    #DEBUG: no owner filter
    #names = db.query(Filename.fileName, Files.id).join(Files).join(Owner).all()

    ret = []
    for c in names:
        #Label is filename, value is file id
        ret.append(dict(label=c[0], value=c[1]))

    ret.append(dict(label="All", value="All"))
    return ret


def gen_margin(l=5, r=5, b=20, t=70):
    return {'l': l, 'r': r, 'b': b, 't': t}
