#!/bin/sh
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &
rq worker -c flaskr.rqsets &>  data/a/streaming.txt &


echo "Running gunicorn server now"
echo $PORT
ps -a | grep rq
exec gunicorn -b :$PORT --access-logfile - --error-logfile - run:app
wait
