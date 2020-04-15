#!/bin/sh
if [ -z "${WORKER}" ]; then
  echo "Not worker"
  echo "Running gunicorn server now"
  echo $PORT
  ps -a | grep rq
  exec gunicorn -b :$PORT --access-logfile - --error-logfile - run:app

  echo "Web mode" > errors.txt
else 
  echo "Worker mode"
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &
  rq worker -c flaskr.rqsets &

  echo "Worker Mode" > errors.txt
  wait
fi
