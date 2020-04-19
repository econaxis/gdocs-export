import os

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = 17608
REDIS_PASSWORD = os.environ["REDIS_PASSW"]


def returnConfig():
    REDIS_HOST = os.environ["REDIS_HOST"]
    REDIS_PORT = 17608
    REDIS_PASSWORD = os.environ["REDIS_PASSW"]
    return dict(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
