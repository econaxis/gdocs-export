import os
import sys

#Necessary for non HTTPS OAUTH calls
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#Adds pydoc path to import directory
sys.path.insert(1, '../')

class Config:
    SECRET_KEY = "dsfjslkfdsjflkdsa;fsajl;fakj"
    HOMEPATH = "/mnt/c/users/henry/documents/pydocs/"
    HOMEDATAPATH = "/mnt/c/users/henry/documents/pydocs/data/"
    PRESERVE_CONTEXT_ON_EXCEPTION = True
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.activity.readonly']
    TEMPLATES_AUTO_RELOAD = True
    

CONF = Config()
