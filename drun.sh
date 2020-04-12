docker stop henry
docker build -t henry2833/pydocs .
docker tag henry2833/pydocs registry.heroku.com/pydocs123/web
docker run -p 5000:5000 -e PORT=5000 --name henry --rm -d henry2833/pydocs
docker logs henry --follow
