import os

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = 17608
REDIS_PASSWORD = os.environ["REDIS_PASSW"]

print(REDIS_HOST, REDIS_PASSWORD)

def returnConfig():
    return dict(host = REDIS_HOST, port = REDIS_PORT, password = REDIS_PASSWORD)
