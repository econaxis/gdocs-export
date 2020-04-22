#!/bin/sh

echo $PWD
export PYTHONPATH=$PWD
echo $SQL_CONN
echo $REDIS_HOST
echo $REDIS_PASSW


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
  exec rq worker -c flaskr.rqsets
fi
