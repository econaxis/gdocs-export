from loader import load
from rq import Queue
from redis import Redis
from pprint import PrettyPrinter
from flaskr.rqsets import returnConfig

import os

homedata = os.environ["HOMEDATAPATH"]
assert homedata

import urllib.request

pp = PrettyPrinter(indent=4)


redis_conn = Redis(**(returnConfig()))

def queueLoad(userid, workingPath, fileId, creds):
    q = Queue(connection=redis_conn)
    #open( workingPath + 'streaming.txt',
    #    'a+').write("Starting (this may take up to 30 minutes) <br>Refresh the page to view updates<br>")

    #TODO: fix path
    import secrets

    token = secrets.token_urlsafe(4)
    ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    name = f"{userid}-{token}"
    job = q.enqueue(load,
                    job_timeout='50h',
                    args=(name, None, fileId, creds))


def spam(i=100):

    import pickle
    creds = pickle.load(open("creds.pickle", 'rb'))
    for i in range(i):
        print(i)
        queueLoad("v2", None, "root", creds)

def spam_threaded():
    import threading

    ths = [threading.Thread(target = spam) for x in range(10)]
    [x.start() for x in ths]
    [x.join() for x in ths]
