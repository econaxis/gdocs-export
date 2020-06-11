#!/bin/bash

apt-get update
apt-get install -y gcc libldap2-dev libsasl2-dev libssl-dev libcurl4-openssl-dev
echo "===="
echo $HOMEPATH
echo $REQ_FILE
echo "===="

pip install --upgrade pip && \
pip install pyopenssl && \
pip install -r installation/proc_reqs.txt