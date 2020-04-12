FROM python:3.8.2

ENV DOCKERENV 1
ENV DOCKERWDIR /app/
WORKDIR ${DOCKERWDIR}

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY flaskr ./flaskr
COPY . .

EXPOSE 5000

RUN chmod +x boot.sh

ENTRYPOINT ["./boot.sh"]