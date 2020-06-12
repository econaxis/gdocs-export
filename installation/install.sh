#!/bin/bash

apt-get update
apt-get install -y gcc libldap2-dev libsasl2-dev libssl-dev libcurl4-openssl-dev


# apk add curl-dev libcurl curl openldap-dev 
echo "===="
echo $HOMEPATH
echo $REQ_FILE
echo "===="

pip install --upgrade pip && \
pip install pyopenssl --user && \
pip install --user -r "installation/proc_reqs.txt"


mkdir -p data/logs
mkdir -p data/dbs
