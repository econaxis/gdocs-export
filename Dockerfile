FROM python:3.8.2-buster

ENV DOCKERENV 1
ENV DOCKERWDIR /app/

WORKDIR ${DOCKERWDIR}



COPY installation ./installation
RUN chmod +x ./installation/instodbc.sh
RUN ./installation/instodbc.sh
RUN pip install --upgrade pip
RUN pip install -r installation/requirements.txt
RUN apt-get update && apt-get install nano vim -y

EXPOSE 5000

COPY secret ./secret

ARG WORKER
ARG REDIS_PASSW
ARG REDIS_HOST
ARG SQL_PASS
ARG SQL_CONN
ARG AZURE
ENV AZURE ${AZURE}
ENV WORKER ${WORKER}
ENV REDIS_PASSW ${REDIS_PASSW}
ENV REDIS_HOST ${REDIS_HOST}
ENV SQL_PASS   ${SQL_PASS}
ENV SQL_CONN ${SQL_CONN}
ENV RQ_NAME=default


RUN chmod +x ./installation/vartest.sh
RUN ./installation/vartest.sh

COPY configlog.py boot.sh loader.py dsds.py run.py Dockerfile ./
COPY data ./data


COPY flaskr ./flaskr
COPY processing ./processing

#RUN chmod +x ./boot.sh

#RUN chmod -R 777 ./

ENTRYPOINT ["./boot.sh"]
