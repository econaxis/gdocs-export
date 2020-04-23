FROM python:3.8.2-buster

ENV DOCKERENV 1
ENV DOCKERWDIR /app/

WORKDIR ${DOCKERWDIR}



COPY installation ./installation
RUN chmod +x ./installation/instodbc.sh && chmod +x ./installation/vartest.sh && chmod +x ./boot.sh
RUN ./installation/instodbc.sh
RUN pip install --upgrade pip && pip install -r installation/requirements.txt && apt-get update && apt-get install nano vim -y

EXPOSE 5000

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


COPY configlog.py boot.sh loader.py dsds.py run.py drun.sh dockerbuild.sh Dockerfile ./
COPY data ./data


COPY flaskr ./flaskr
COPY processing ./processing


RUN chmod -R 777 ./

ENTRYPOINT ["./boot.sh"]
