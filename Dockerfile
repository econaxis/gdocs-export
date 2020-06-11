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


COPY . .


ENTRYPOINT ["./boot.sh"]
