#!/bin/bash
export REDIS_PASSW=KgPh6DCLJ8tr1dq6TkiG66otuiC3GPqE
export SQL_PASS=Infoip32
export REDIS_HOST=redis-17608.c53.west-us.azure.cloud.redislabs.com

export SQL_CONN=Driver%3D%7BODBC+Driver+17+for+SQL+Server%7D%3BServer%3Dtcp%3Apydoc-db.database.windows.net%2C1433%3BDatabase%3Dpydocs%3BUid%3Dhenry2833%3BPwd%3D%7BInfoip32%7D%3BEncrypt%3Dyes%3BTrustServerCertificate%3Dno%3BConnection+Timeout%3D30%3B

export AZURE=true
echo "worker count: $AZ_WORKER_COUNT"
export RQ_NAME=ec2-rq
export WORKER=true



procname="ec2${2:-$RANDOM}"
RQ_NAME="${RQ_NAME}$procname"
echo $RQ_NAME
echo $procname


docker pull henry2833/pydocs:latest

echo "Done build"

docker network create --driver bridge pydocs-net

echo "Done network"


if [ "$3" == "w" ]; then
    docker run -m 170m --memory-swap 400m --memory-swappiness 60 --network pydocs-net \
        -e REDIS_PASSW -e SQL_CONN -e REDIS_HOST -e AZURE -e AZ_WORKER_COUNT -e RQ_NAME \
        -e WORKER --rm -d --name "$procname" henry2833/pydocs:latest
elif [ "$3" == "a" ]; then
    docker run -m 300m --memory-swap 500m -e PORT=5000 -e REDIS_HOST -e REDIS_PASSW -e SQL_CONN -e SQL_SERV=true \
        --name sql_serv --network pydocs-net --rm -d henry2833/pydocs:latest

    docker run -m 150m --memory-swap 400m --memory-swappiness 90 --network pydocs-net \
        -e REDIS_PASSW -e SQL_CONN -e REDIS_HOST -e AZURE -e AZ_WORKER_COUNT -e RQ_NAME \
        -e WORKER --rm -d --name "$procname" henry2833/pydocs:latest

fi
docker logs $procname --follow
