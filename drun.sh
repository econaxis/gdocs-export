
if [-z "$2" ]; then
    docker stop henry
fi
docker build -t henry2833/pydocs --build-arg REDIS_HOST --build-arg REDIS_PASSW --build-arg SQL_CONN .

if [ -z "$1" ]; then
    docker run -p 5000:5000 -e PORT=5000 -e WORKER=true --name henry --rm -d henry2833/pydocs
else
    docker run -p 5000:5000 -e PORT=5000 --name henry --rm -d henry2833/pydocs
fi
docker logs henry --follow
