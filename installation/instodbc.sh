#!/bin/bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

#Download appropriate package for the OS version
#Choose only ONE of the following, corresponding to your OS version

#Debian 8
curl https://packages.microsoft.com/config/debian/8/prod.list > /etc/apt/sources.list.d/mssql-release.list

#Debian 9
curl https://packages.microsoft.com/config/debian/9/prod.list > /etc/apt/sources.list.d/mssql-release.list

#Debian 10
curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list

apt-get update && apt-get install -y build-essential unixodbc-dev unixodbc
ACCEPT_EULA=Y apt-get install -y msodbcsql17
# optional: for bcp and sqlcmd
# sudo ACCEPT_EULA=Y apt-get install mssql-tools
# echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile
# echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc
# source ~/.bashrc
# # optional: for unixODBC development headers
# sudo apt-get install unixodbc-dev
# # optional: kerberos library for debian-slim distributions
# sudo apt-get install libgssapi-krb5-2
