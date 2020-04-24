from loader import load
from rq import Queue
from redis import Redis
from pprint import PrettyPrinter
from flaskr.rqsets import returnConfig

pp = PrettyPrinter(indent=4)


def queueLoad(userid, workingPath, fileId, creds):
    redis_conn = Redis(**(returnConfig()))
    q = Queue(connection=redis_conn)
    #open( workingPath + 'streaming.txt',
    #    'a+').write("Starting (this may take up to 30 minutes) <br>Refresh the page to view updates<br>")

    #TODO: fix path
    import secrets

    token = secrets.token_urlsafe(6)
    job = q.enqueue( load, job_timeout='50h', args=( f"testing123{token}", f"/app/data/testing123{token}/", fileId, creds))

def spam(i = 100):
    import pickle
    creds = pickle.load(open("creds.pickle", 'rb'))
    for i in range(i):
        queueLoad("testing123", "/app/data/testing123/", "root", creds)
