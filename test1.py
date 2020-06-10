import pycurl
import certifi
import time
import pickle
from processing.datutils.test_utils import TestUtil as tu

from io import BytesIO

headers = {}
def header_function(header_line):
    # HTTP standard specifies that headers are encoded in iso-8859-1.
    # On Python 2, decoding step can be skipped.
    # On Python 3, decoding step is required.
    header_line = header_line.decode('iso-8859-1')

    # Header lines include the first status line (HTTP/1.x ...).
    # We are going to ignore all lines that don't have a colon in them.
    # This will botch headers that are split on multiple lines...
    if ':' not in header_line:
        return

    # Break the header line into header name and value.
    name, value = header_line.split(':', 1)

    # Remove whitespace that may be present.
    # Header lines include the trailing newline, and there may be whitespace
    # around the colon.
    name = name.strip()
    value = value.strip()

    # Header names are case insensitive.
    # Lowercase name here.
    name = name.lower()

    # Now we can actually record the header name and value.
    # Note: this only works when headers are not duplicated, see below.
    headers[name] = value

tu.refresh_creds(pickle.load(open('creds.pickle', 'rb')))
creds = tu.creds


buffer = BytesIO()

base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'.format(file_id = "1JEcM-IFEodRvDg7EE9AntQ4wwOBTRXcDFqRK5SR2I08", end = 250)


#base_url = "https://en3ewne6iq6wm.x.pipedream.net"

c = pycurl.Curl()



s = []

t = 0
import requests

for i in range (30):
    a1 =time.time()
    response = requests.get(url = base_url, headers = tu.headers)
    s.append(response.text)
    t+= time.time() - a1
    time.sleep(0.2)

print('req time: ', t)


t = 0

for i in range(30):
    a1 = time.time()
    c.setopt(c.CAINFO, certifi.where())
    c.setopt(c.URL,base_url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(pycurl.HTTPHEADER, ['authorization: '+ tu.headers['authorization']])
    c.perform()
    s.append(buffer.getvalue().decode('iso-8859-1'))
    t += time.time() - a1
    time.sleep(0.2)



print("pycurl time: ", t)


# HTTP response code, e.g. 200.
# print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
# # Elapsed time for the transfer.
# print('Time: %f' % c.getinfo(c.TOTAL_TIME))
#
# # getinfo must be called before close.
# c.close()
