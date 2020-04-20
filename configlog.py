import logging
import socket
from logging import FileHandler, StreamHandler
from logging.handlers import SysLogHandler



logging.basicConfig(level=logging.DEBUG, filename = "logs.txt", filemode = "w")


formatter =logging.Formatter("%(name)s %(filename)s %(funcName)s %(lineno)d - %(message)s")


syslog = SysLogHandler(address=('logs2.papertrailapp.com', 49905))
filelog = FileHandler("logs.txt")
stream = StreamHandler()

syslog.setFormatter(formatter)
filelog.setFormatter(formatter)
stream.setFormatter(formatter)



logger = logging.getLogger()
logger.addHandler(syslog)
logger.addHandler(filelog)
logger.addHandler(stream)

logger.setLevel(logging.NOTSET)

