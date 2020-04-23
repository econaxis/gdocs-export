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


if [ "$2" = "o" ]
then
    echo "openshift"
    opens=default-route-openshift-image-registry.apps.us-east-2.starter.openshift-online.com/pydocs/pydocs
    docker tag henry2833/pydocs:$1 $opens:$1
    docker push $opens:$1
fi
