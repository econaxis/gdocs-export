import os
import logging
from flask_caching import Cache
import sys


# Necessary for non HTTPS OAUTH calls
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Adds pydoc path to import directory
sys.path.insert(1, '../')


class Config:
    SECRET_KEY = "dsfjslkfdsjflkdsa;fsajl;fakj"

    if('FLASKDBG' in os.environ):
        HOMEPATH = "/home/henry/pydocs/"
        HOMEDATAPATH = "/home/henry/pydocs/data/"
    elif('DOCKERENV' in os.environ):
        HOMEPATH = os.environ["DOCKERWDIR"]
        HOMEDATAPATH = HOMEPATH + 'data/'
    else:
        HOMEPATH = "/app/"
        HOMEDATAPATH = "/app/data/"
    PRESERVE_CONTEXT_ON_EXCEPTION = True
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    SCOPES = [ 'https://www.googleapis.com/auth/drive']
    TEMPLATES_AUTO_RELOAD = True


CONF = Config()
cache = Cache(config={"CACHE_TYPE": 'simple'})
