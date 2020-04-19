docker stop henry
docker build -t henry2833/pydocs --build-arg REDIS_HOST --build-arg REDIS_PASSW --build-arg SQL_PASS .
docker tag henry2833/pydocs registry.heroku.com/pydocs123/web
docker run -p 5000:5000 -e PORT=5000 --name henry --rm -d henry2833/pydocs
docker logs henry --follow
