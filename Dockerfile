FROM python:3.8.5-slim-buster

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

EXPOSE 2222 80
WORKDIR /app
COPY . .
ENV FLASK_APP flask_api.py
ENV FLASK_ENV development
ENTRYPOINT ["flask", "run", "-p", "80", "--host=0.0.0.0"]
