#!/bin/sh
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
rq worker -c flaskr.rqsets &>  streaming.txt &
exec rq worker -c flaskr.rqsets &>  streaming.txt &
wait

