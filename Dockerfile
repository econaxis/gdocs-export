FROM python:3.8.2-buster

ENV DOCKERENV 1
ENV DOCKERWDIR /app/

WORKDIR ${DOCKERWDIR}



COPY installation ./installation

RUN chmod +x ./installation/instodbc.sh && \
    ./installation/instodbc.sh && \ 
    pip install --upgrade pip && \ 
    pip install -r installation/requirements.txt && \
    apt-get update && apt-get install nano vim -y


#EXPOSE 5000

COPY secret ./secret

ARG WORKER
ARG REDIS_PASSW
ARG REDIS_HOST
ARG SQL_PASS
ARG SQL_CONN
ARG AZURE 

ENV AZURE=${AZURE} \
    WORKER=${WORKER} \
    REDIS_PASSW=${REDIS_PASSW} \
    REDIS_HOST=${REDIS_HOST} \
    SQL_PASS=${SQL_PASS} \
    SQL_CONN=${SQL_CONN} \
    RQ_NAME=default



COPY configlog.py boot.sh loader.py dsds.py run.py Dockerfile ./
COPY data ./data


COPY flaskr ./flaskr
COPY processing ./processing

#RUN chmod +x ./boot.sh

#RUN chmod -R 777 ./


ENTRYPOINT ["./boot.sh"]
