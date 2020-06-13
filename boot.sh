#!/bin/sh


echo "STARTING"

if [ -n "${WORKER}" ]; then
    echo "Worker mode"
    rq worker -c flaskr.rqsets &
    exec rq worker -c flaskr.rqsets
else 
    echo "Not worker"
    echo "Running gunicorn server now"
    exec gunicorn -b :$PORT --access-logfile=access.txt --error-logfile - --log-syslog \
            --log-level debug --preload \
            --timeout=120 --workers=2 --threads=2 run:app
    echo "Web mode" > errors.txt
    wait
fi

wait
