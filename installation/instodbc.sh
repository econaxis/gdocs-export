#!/bin/bash

# curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
# #
# #Download appropriate package for the OS version
# #Choose only ONE of the following, corresponding to your OS version
# 
# #Debian 10
# curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
# 
# echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc
# source ~/.bashrc
# # optional: for unixODBC development headers
# apt-get install -y unixodbc-dev
# # optional: kerberos library for debian-slim distributions
# apt-get install -y libgssapi-krb5-2


apt-get update
apt-get install -y cifs-utils gcc g++ libsasl2-dev libldap2-dev libssl-dev
#Setup Azure storage mounting 

#resourceGroupName="pydocs"
#storageAccountName="pydocs"
#
### This command assumes you have logged in with az login
##httpEndpoint=$(az storage account show \
##--resource-group $resourceGroupName \
##--name $storageAccountName \
##--query "primaryEndpoints.file" | tr -d '"')
##smbPath=$(echo $httpEndpoint | cut -c7-$(expr length $httpEndpoint))
##fileHost=$(echo $smbPath | tr -d "/")
##
##nc -zvw3 $fileHost 445
#
#STORAGEACCT="pydocs"
#STORAGEKEY=$AZURESTORAGEKEY
#
#
#echo "Storage key: ${STORAGEKEY}, path: ${STORAGE_PATH}"
#
#mkdir -p  /mnt/${STORAGE_PATH}
#
#mount -t cifs //$STORAGEACCT.file.core.windows.net/def ${STORAGE_PATH::-1} -o vers=3.0,username=$STORAGEACCT,password=$STORAGEKEY,dir_mode=0777,file_mode=0777,serverino
#
#echo "================"
#echo "$(cat ${STORAGE_PATH}test.txt)"
#echo "================"


echo "===="

echo $HOMEPATH
echo $REQ_FILE


echo "===="



pip install --upgrade pip && \ 
pip install pyopenssl && \
pip install -r installation/${REQ_FILE} && \


apt-get purge -y cifs-utils build-essential libsasl2-dev libldap2-dev libssl-dev
apt-get autoremove -y
echo "Installation done!"
