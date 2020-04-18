docker build -t henry2833/pydocs:$1 .

if [ "$2" = "y" ]
then
  echo "pushing to registry"
  docker tag henry2833/pydocs:$1 registry.heroku.com/pydocs123/$3
  docker push registry.heroku.com/pydocs123/$3
  heroku container:release $3
fi

if [ "$2" = "p" ]
then
  echo "pushing"
  docker push henry2833/pydocs:$1
fi

