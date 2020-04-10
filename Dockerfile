FROM python:3.8.2

WORKDIR /app/

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

RUN chmod +x boot.sh

ENTRYPOINT ["./boot.sh"]
