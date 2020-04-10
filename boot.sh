#!/bin/sh
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &
rq worker -c flaskr.rqsets &


echo "Running gunicorn server now"
echo $PORT
exec gunicorn -b :$PORT --access-logfile - --error-logfile - run:app
