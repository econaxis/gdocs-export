#!/bin/bash
resourceGroupName="pydocs"
storageAccountName="pydocs"

## This command assumes you have logged in with az login
#httpEndpoint=$(az storage account show \
#--resource-group $resourceGroupName \
#--name $storageAccountName \
#--query "primaryEndpoints.file" | tr -d '"')
#smbPath=$(echo $httpEndpoint | cut -c7-$(expr length $httpEndpoint))
#fileHost=$(echo $smbPath | tr -d "/")
#
#nc -zvw3 $fileHost 445

AZURESTORAGEKEY="M7ReBg04PlL6QrpelQJAi2zkrhiqOfYRberVZgarvu4AdS7Le+Cu+sTOnJ1nOl57KUmmMN5bm75vj0TP136xAQ=="
STORAGEACCT="pydocs"
STORAGEKEY=$AZURESTORAGEKEY
STORAGE_PATH=/mnt/az-pydocs/


echo "Storage key: ${STORAGEKEY}, path: ${STORAGE_PATH}"

mkdir -p  /mnt/${STORAGE_PATH}

mount -t cifs //$STORAGEACCT.file.core.windows.net/def ${STORAGE_PATH::-1} -o vers=3.0,username=$STORAGEACCT,password=$STORAGEKEY,dir_mode=0777,file_mode=0777,serverino

echo "================"
echo "$(cat ${STORAGE_PATH}test.txt)"
echo "================"
