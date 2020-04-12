docker build -t henry2833/pydocs .

if [ "$1" = "y" ]
then
  echo "pushing to registry"
  docker tag henry2833/pydocs registry.heroku.com/pydocs123/$2
  docker push registry.heroku.com/pydocs123/$2
  heroku container:release $2
fi


