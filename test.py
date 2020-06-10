import pycurl
import certifi
from io import BytesIO
c = pycurl.Curl()

def f(s):
    buffer = BytesIO()
    c.setopt(c.URL, 'http://pycurl.io/')
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.perform()


    body = buffer.getvalue()
    # Body is a byte string.
    # We have to know the encoding in order to print it to a text file
    # such as standard output.
    print(body.decode('iso-8859-1'))

def c():
    c.close()

