import logging
import os
import sys
import socket
from logging import FileHandler, StreamHandler
from logging.handlers import SysLogHandler

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


logging.basicConfig(level=logging.DEBUG)


formatter =logging.Formatter(f"{bcolors.BOLD}%(name)s {bcolors.ENDC} %(asctime)s{bcolors.BOLD} %(funcName)s{bcolors.ENDC} %(lineno)d :\n %(message)s")

specform =logging.Formatter(f"{bcolors.BOLD}%(name)s {bcolors.ENDC} %(asctime)s{bcolors.BOLD}\
        %(funcName)s{bcolors.ENDC} %(lineno)d :\n {bcolors.OKGREEN} %(message)s {bcolors.ENDC}")


#syslog = SysLogHandler(address=('syslog-a.logdna.com', 49905))

syslog = SysLogHandler(address=('logs2.papertrailapp.com', 49905))
filelog = FileHandler("logs.txt")
stream = StreamHandler()


syslog.setFormatter(formatter)
filelog.setFormatter(formatter)
stream.setFormatter(formatter)

syslog1 = SysLogHandler(address=('logs2.papertrailapp.com', 49905))
filelog1 = FileHandler("logs.txt")
stream1 = StreamHandler()



stream.setLevel(logging.INFO)
stream1.setLevel(logging.INFO)



stream1.setFormatter(specform)

logger = logging.getLogger()
logger.addHandler(syslog)
logger.addHandler(filelog)
logger.addHandler(stream)

logger.setLevel(logging.DEBUG)


gdrive = logging.getLogger("googleapiclient")
gdrive.propagate = False
gdrive.setLevel(logging.WARNING)
gdrive.addHandler(filelog)


asynclog = logging.getLogger("asyncio")
asynclog.propagate = False
asynclog.addHandler(filelog)

urlliblog = logging.getLogger('urllib3')
urlliblog.propagate = False
urlliblog.addHandler(filelog)


operationlog = logging.getLogger('gdocrevisions.operation')
operationlog.propagate = False
operationlog.addHandler(filelog)

utillog = logging.getLogger('processing')
utillog.propagate = False
utillog.addHandler(stream1)

utillog = logging.getLogger('flaskr')
utillog.propagate = False
utillog.addHandler(stream1)

Profiler = None


def handle_exception(exc_type, exc_value, exc_traceback):
    return


    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    if(Profiler != None):
        logger.critical('dumped stats')
        Profiler.dump_stats('profiler')

    import smtplib, ssl
    port = 465
    password = "henryrage"
    email = "martinliu24@gmail.com"
    context = ssl.create_default_context()

    log = """\
        Subject: PYDOCSLOGS

        This message is sent from Pydocs Logging
        """

    log += open('logs.txt', 'r').read()


    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:

        server.login(email, password)
        server.sendmail(email, "henry2833+py@gmail.com", log)


    logger.critical("exiting! from sshook")

    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    return


#sys.excepthook = handle_exception

