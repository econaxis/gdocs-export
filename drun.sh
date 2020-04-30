
name=${1:-henry}
docker stop $name


docker build -t henry2833/pydocs --build-arg REDIS_HOST --build-arg REDIS_PASSW --build-arg SQL_CONN .

echo "Done build"

docker network create --driver bridge pydocs-net

echo "Done network"


if [ "$2" == "s" ]; then
    docker run -e PORT=5000 -e SQL_SERV=true --name $name --rm -d henry2833/pydocs
elif [ "$2" == "d" ]; then
e   docker run -p 5000:5000 -e PORT=5000 --entrypoint python --name $name --rm -d henry2833/pydocs dsds.py
elif [ "$2" == "a" ]; then
    docker run -m 200m -p 5000:5000 -e PORT=5000  -e WORKER -e REDIS_PASSW -e SQL_CONN -e REDIS_HOST -e WORKER=true --name $name --rm -d --network pydocs-net henry2833/pydocs
    docker run -m 200m -e PORT=5000 -e REDIS_HOST -e REDIS_PASSW -e SQL_CONN -e SQL_SERV=true --name sql_serv --network pydocs-net --rm -d henry2833/pydocs
fi
docker logs $name --follow
