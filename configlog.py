import logging
import smtplib
import time
import os
import sys
from logging import FileHandler, StreamHandler
from logging.handlers import SysLogHandler
from datetime import datetime
import secrets
import urllib.request


token = secrets.token_urlsafe(4)

os.environ["TZ"]="America/Vancouver"
time.tzset()


logFile = "data/logs/logs{}---{}.txt".format(datetime.now().strftime("%-m-%d"), token)

syslog = SysLogHandler(address=('logs2.papertrailapp.com', 49905))
filelog = FileHandler(logFile)
stream = StreamHandler()

stream.setLevel(logging.INFO)
filelog.setLevel(logging.NOTSET)

def semidisable(logg):
    logg.propagate=False
    logg.setLevel(logging.DEBUG)
    logg.addHandler(filelog)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


myip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
formatter =logging.Formatter(f"%(filename).8s:%(asctime)s:%(funcName)s:%(lineno)d:{token} -- %(message)s", "%d,%H:%M:%S")

#syslog = SysLogHandler(address=('syslog-a.logdna.com', 49905))



syslog.setFormatter(formatter)
filelog.setFormatter(formatter)
stream.setFormatter(formatter)



logger = logging.getLogger()
logger.addHandler(syslog)
logger.addHandler(filelog)
logger.addHandler(stream)

logger.setLevel(logging.NOTSET)


semidisable( logging.getLogger("googleapiclient"))
semidisable( logging.getLogger("asyncio"))
semidisable( logging.getLogger('urllib3'))
semidisable( logging.getLogger('gdocrevisions.operation'))

sqlal = logging.getLogger('sqlalchemy')
sqlal.setLevel(logging.DEBUG)
sqlal.propagate = False
sqlal.addHandler(filelog)
#semidisable( logging.getLogger('sqlalchemy.engine'))




Profiler = None


def handle_exception(exc_type, exc_value, exc_traceback):

    logger.critical("Custom Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sendmail(msg = "Program ended wih exception. Check logs for more details")
    logger.critical("exiting! from sshook")

    #logger.info("sending to default hook")
    return 0 


sys.excepthook = handle_exception

import smtplib

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import multiprocessing as mp
import random

def sendmail(msg = "", return_thread = False):


    p = mp.Process(target = mp_sendmail, args = (msg, ))
    p.start()

    if return_thread:
        return p
    else:
        p.join()
        return


def mp_sendmail(msg):
    logger.info("sending mail")
    subject = f"PYDOCS LOGS from {myip}::{token}"
    body = f"Automatically generated logging from {myip}\nSent date: {datetime.now().__str__()}\n\n{msg}"
    sender_email = "postmaster@sandboxafcb93d604f547c984f76fd927c84de2.mailgun.org"
    receiver_email = "henry2833+py@gmail.com"
    password = "efa1a3633640e1dd88cb3bc01f934dab"

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message["Bcc"] = receiver_email  # Recommended for mass emails

    # Add body to email
    message.attach(MIMEText(body, "plain"))


    # Open PDF file in binary mode
    with open(logFile, 'r') as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {logFile}",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    text = message.as_string()

    # Log in to server using secure context and send email
    with smtplib.SMTP("smtp.mailgun.org", 587) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)

    return
