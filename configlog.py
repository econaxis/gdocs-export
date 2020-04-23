import logging
import smtplib, ssl
import os
import sys
import socket
from logging import FileHandler, StreamHandler
from logging.handlers import SysLogHandler
from datetime import datetime


logFile = "data/logs/logs%s.txt"%datetime.now().strftime("%-m-%d-%H:%M")

syslog = SysLogHandler(address=('logs2.papertrailapp.com', 49905))
filelog = FileHandler(logFile)
stream = StreamHandler()

stream.setLevel(logging.INFO)
filelog.setLevel(logging.NOTSET)

def semidisable(logg):
    logg.propagate=False
    logg.setLevel(logging.NOTSET)
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


formatter =logging.Formatter(f"%(name)s %(asctime)s %(funcName)s %(lineno)d :\n %(message)s\n")

#syslog = SysLogHandler(address=('syslog-a.logdna.com', 49905))



syslog.setFormatter(formatter)
filelog.setFormatter(formatter)
stream.setFormatter(formatter)



logger = logging.getLogger()
logger.addHandler(syslog)
logger.addHandler(filelog)
logger.addHandler(stream)

logger.setLevel(logging.DEBUG)


semidisable( logging.getLogger("googleapiclient"))
semidisable( logging.getLogger("asyncio"))
semidisable( logging.getLogger('urllib3'))
semidisable( logging.getLogger('gdocrevisions.operation'))
semidisable( logging.getLogger('sqlalchemy'))
semidisable( logging.getLogger('sqlalchemy.engine'))




Profiler = None


def handle_exception(exc_type, exc_value, exc_traceback):

    logger.critical("Custom Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sendmail()

    logger.critical("exiting! from sshook")

    logger.info("sending to default hook")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    logger.info("done")
    return


sys.excepthook = handle_exception
import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendmail():
    subject = "PYDOCS LOGS"
    body = "Automatically generated logging"
    sender_email = "martinliu24@gmail.com"
    receiver_email = "henry2833+py@gmail.com"
    password = "henryrage"

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message["Bcc"] = receiver_email  # Recommended for mass emails

    # Add body to email
    message.attach(MIMEText(body, "plain"))


    # Open PDF file in binary mode
    with open(logFile, "rb") as attachment:
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
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)
