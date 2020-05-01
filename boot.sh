#!/bin/sh


echo "STARTING"

echo $PWD
export PYTHONPATH=$PWD
echo $SQL_CONN
echo $REDIS_HOST
echo $REDIS_PASSW
echo $RQ_NAME

echo $SQL_SERV

if [ -n "$SQL_SERV" ]; then
    echo "SQL SERVER MODE"
    python -u -m processing.sql_server
    wait
elif [ -n "${WORKER}" ]; then
    echo "Worker mode"
    rq worker -c flaskr.rqsets &
    exec rq worker -c flaskr.rqsets
else 
    echo "Not worker"
    echo "Running gunicorn server now"
    echo $SQL_CONN
    echo $PORT
    exec gunicorn -b :$PORT --access-logfile - --error-logfile - run:app
    echo "Web mode" > errors.txt
    wait
fi

wait
