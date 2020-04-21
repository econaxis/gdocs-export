FROM python:3.8.2-buster

ENV DOCKERENV 1
#ENV DOCKERWDIR /app/

#WORKDIR ${DOCKERWDIR}



COPY installation ./installation
RUN chmod +x ./installation/instodbc.sh
RUN ./installation/instodbc.sh
RUN pip install --upgrade pip
RUN pip install -r installation/requirements.txt
RUN apt-get update && apt-get install nano vim -y

EXPOSE 5000
COPY boot.sh ./
RUN chmod +x boot.sh

COPY secret ./secret

ARG WORKER
ARG REDIS_PASSW
ARG REDIS_HOST
ARG SQL_PASS
ARG SQL_CONN
ENV WORKER ${WORKER}
ENV REDIS_PASSW ${REDIS_PASSW}
ENV REDIS_HOST ${REDIS_HOST}
ENV SQL_PASS   ${SQL_PASS}
ENV SQL_CONN ${SQL_CONN}

#COPY configlog.py loader.py dsds.py run.py drun.sh dockerbuild.sh Dockerfile ./
#COPY gdocrevisions ./gdocrevisions
#COPY data ./data

FROM mcr.microsoft.com/azure-functions/python:3.0-python3.8

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true


COPY . /home/site/wwwroot

#COPY flaskr ./flaskr
#COPY processing ./processing


ENTRYPOINT ["./home/site/wwwroot/boot.sh"]
