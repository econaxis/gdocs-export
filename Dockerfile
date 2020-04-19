FROM python:3.8.2

ENV DOCKERENV 1
ENV DOCKERWDIR /app/
WORKDIR ${DOCKERWDIR}

COPY installation ./installation

RUN chmod +x ./installation/instodbc.sh

RUN ./installation/instodbc.sh
RUN pip install -r ./installation/requirements.txt

EXPOSE 5000
COPY boot.sh ./
RUN chmod +x boot.sh

ARG WORKER
ENV WORKER ${WORKER}
ARG REDIS_PASSW
ARG REDIS_HOST
ARG SQL_PASS
ARG SQL_CONN
ENV REDIS_PASSW ${REDIS_PASSW}
ENV REDIS_HOST ${REDIS_HOST}
ENV SQL_PASS   ${SQL_PASS}
ENV SQL_CONN ${SQL_CONN}

COPY run.py service.json drun.sh dockerbuild.sh Dockerfile ./
COPY data ./data

COPY flaskr ./flaskr
COPY processing ./processing

ENTRYPOINT ["./boot.sh"]
