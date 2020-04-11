docker build -t henry2833/pydocs .
docker tag henry2833/pydocs registry.heroku.com/pydocs123/web

if [ -z "$1"]
then
  echo "pushing to registry"
  docker push registry.heroku.com/pydocs123/web
fi
