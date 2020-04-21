from loader import load
from rq import Queue
from redis import Redis
from pprint import PrettyPrinter
from flaskr.rqsets import returnConfig

pp = PrettyPrinter(indent=4)


def queueLoad(userid, workingPath, fileId, creds):
    print("queue load triggered for ", userid, fileId)
    redis_conn = Redis(**(returnConfig()))
    q = Queue(connection=redis_conn)
    open(
        workingPath +
        'streaming.txt',
        'a+').write("Starting (this may take up to 30 minutes) <br>Refresh the page to view updates<br>")

    #TODO: fix path
    job = q.enqueue( load, job_timeout='50h', args=( "testing123", "/app/data/testing123/", fileId, creds))
