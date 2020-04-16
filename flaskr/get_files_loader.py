import pickle
from processing.get_files import loadFiles
from rq import Queue
from redis import Redis
from pprint import PrettyPrinter
from flaskr.rqsets import returnConfig

pp = PrettyPrinter(indent =4 )


def queueLoad(userid, workingPath, fileId, creds):
    print("queue load triggered for ", userid, fileId)
    pp.pprint(creds)
    redis_conn = Redis(**(returnConfig()))
    pp.pprint(returnConfig())
    q = Queue (connection = redis_conn)
    open(workingPath + 'streaming.txt', 'a+').write("Starting (this may take up to 30 minutes) <br>Refresh the page to view updates<br>")
    job = q.enqueue(loadFiles, job_timeout = '50h', args = (userid, workingPath, fileId, creds))


