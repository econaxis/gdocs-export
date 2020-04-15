FROM python:3.8.2

ENV DOCKERENV 1
ENV DOCKERWDIR /app/
WORKDIR ${DOCKERWDIR}

COPY installation ./installation

RUN chmod +x ./installation/instodbc.sh

RUN ./installation/instodbc.sh
RUN pip install -r ./installation/requirements.txt

EXPOSE 5000

ARG WORKER
ENV WORKER ${WORKER}
ARG REDIS_PASSW
ARG REDIS_HOST
ARG SQL_PASS
ENV REDIS_PASSW ${REDIS_PASSW}
ENV REDIS_HOST ${REDIS_HOST}
ENV SQL_PASS   ${SQL_PASS}


COPY flaskr ./flaskr
COPY processing ./processing
COPY . .

RUN chmod +x boot.sh
ENTRYPOINT ["./boot.sh"]
