#!/bin/sh

export PYTHONPATH=$PWD
echo $SQL_CONN
echo $REDIS_HOST
echo $REDIS_PASSW

rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &

if [ -z "${WORKER}" ]; then
  echo "Not worker"
  echo "Running gunicorn server now"
  echo $SQL_CONN
  echo $PORT
  exec gunicorn -b :$PORT --access-logfile - --error-logfile - run:app
  echo "Web mode" > errors.txt
  wait
else 
  echo "Worker mode"
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  echo "Worker Mode" > errors.txt
  wait
fi
