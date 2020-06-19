#!/bin/bash

docker pull henry2833/pydocs:compile
docker pull henry2833/pydocs:latest

docker build --target compile \
    --cache-from=henry2833/pydocs:compile \
    --tag=henry2833/pydocs:compile .

docker build --target run \
    --cache-from=henry2833/pydocs:compile \
    --cache-from=henry2833/pydocs:latest \
    --tag=henry2833/pydocs:latest .


docker push henry2833/pydocs:compile
docker push henry2833/pydocs:latest
