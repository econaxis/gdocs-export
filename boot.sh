#!/bin/sh


echo "STARTING"

echo $PWD
export PYTHONPATH=$PWD
echo $SQL_CONN
echo $REDIS_HOST
echo $REDIS_PASSW
echo $RQ_NAME

if [ -n "$AZURE" ]; then
    echo "Azure Worker mode"

    for i in $(seq 1 $AZ_WORKER_COUNT);
    do
        name=${RQ_NAME}$i
        
        echo "name: ${name}"
        rq worker -c flaskr.rqsets --name ${name} &
    done

elif [ -z "${WORKER}" ]; then
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

wait
