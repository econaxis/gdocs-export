FROM python:3.8.2-slim

ENV DOCKERENV 1

ARG HOMEPATH=/app/

WORKDIR ${HOMEPATH}

ARG REQ_FILE=requirements.txt

COPY ./installation ./installation

RUN ls -a && ls installation

RUN chmod +x ./installation/install.sh && \
    ./installation/install.sh && \
    echo "Installation done!"


#COPY . .


#EXPOSE 5000

#ARG WORKER
#ARG REDIS_PASSW
#ARG REDIS_HOST
#ARG SQL_PASS
#ARG SQL_CONN
#ARG AZURE 
#
#ENV AZURE=${AZURE} \
#    WORKER=${WORKER} \
#    REDIS_PASSW=${REDIS_PASSW} \
#    REDIS_HOST=${REDIS_HOST} \
###    SQL_PASS=${SQL_PASS} \
#    SQL_CONN=${SQL_CONN} \
#    RQ_NAME=default



#RUN chmod +x ./boot.sh

#RUN chmod -R 777 ./

ENTRYPOINT ["./boot.sh"]
