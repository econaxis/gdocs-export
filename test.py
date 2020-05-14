"""
import asyncio
import random
import pickle
import secrets

import logging

logger = logging.getLogger(__name__)
per = 1000000000


big = ['fdsafsadfsadfsadfsavsadf;salfjfdsalkajdsafd' * 1000000]

async def adv_read(reader):
    import struct
    header = await reader.readexactly(9)
    header = struct.unpack('!Q?', header)

    to_pickle = header[1]
    length = header[0]

    data = []

    _length = length

    per_read = 1000

    while length > 0:
        try:
            data.append(await reader.readexactly(min(length, per_read)))

        except asyncio.IncompleteReadError as e:
            data.append(e.partial)
            length -= len(e.partial)
        else:
            length -= min(length, per_read)

    data = b"".join(data)

    print("length of read: ", len(data), _length)

    if to_pickle:
        return pickle.loads(data)
    else:
        return data

async def adv_write(writer, data, to_pickle = False):
    import struct

    if to_pickle:
        data = pickle.dumps(data)

    print("length of write: %d", len(data))

    header = struct.pack('!Q?', len(data), to_pickle)

    print(header)

    writer.write(header)
    writer.write(data)
    await writer.drain()

    return

async def connect(message, id = "default"):
    print("connect working")
    r, w = await asyncio.open_connection('127.0.0.1', 8888)

    await adv_write(w, big, to_pickle = True)

    print(len(data))
    print("cnn done")
    w.close()


async def handle_echo(reader, writer):
    print("starting handle_echo")

    data = await adv_read(reader)

    print("received",  len(data),  flush = True)

    writer.close()

    print("done")

async def main():
    server = await asyncio.start_server(
        handle_echo, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    p = [asyncio.create_task(connect(i, id = f"id: {i}")) for i in range(1)]


    async with server:
        await server.serve_forever()


import requests

from itertools import cycle
#If you are copy pasting proxy ips, put in the list below
#proxies = ['121.129.127.209:80', '124.41.215.238:45169', '185.93.3.123:8080', '194.182.64.67:3128', '106.0.38.174:8080', '163.172.175.210:3128', '13.92.196.150:8080']

proxies = [
    "108.61.190.167:8080", "104.244.77.254:8080", "104.207.134.150:8080",
    "103.58.73.94:80", "104.42.112.12:8080", "103.83.38.155:5836",
    "104.250.34.179:80", "112.133.214.244:80", "112.133.214.241:80",
    "101.50.1.2:80", "103.28.121.58:3128", "103.35.132.50:36555",
    "109.172.43.35:3129", "110.78.184.157:8080", "102.164.199.78:48713",
    "1.2.183.80:8080", "109.196.127.35:8888", "109.167.207.72:8080",
    "1.10.188.202:8080", "115.218.212.143:9000", "115.218.2.192:9000",
    "118.175.93.171:32866", "117.212.192.38:8080", "116.197.131.46:8080",
    "116.90.229.186:55890", "118.70.12.171:53281", "117.1.16.131:8080",
    "118.97.36.21:8080", "118.97.29.117:8080", "119.2.41.182:3888",
    "118.99.102.5:8080", "12.139.101.97:80", "12.139.101.100:80",
    "118.69.50.154:80", "123.108.200.106:83", "118.99.102.132:50179",
    "121.52.140.95:8080", "119.252.162.69:8080", "124.29.238.208:8080",
    "124.158.179.13:8080", "119.93.129.106:8080", "122.154.72.102:8080",
    "124.108.19.121:8080", "122.176.32.52:8080", "122.154.200.101:80",
    "125.24.135.214:8080", "119.28.215.215:3003", "125.25.82.191:8080",
    "124.105.197.141:8080", "121.122.96.91:8080", "125.166.161.162:8080",
    "125.209.116.14:8080", "120.28.218.28:3128", "119.42.67.162:8080",
    "125.161.150.119:8080", "121.58.246.247:8080", "124.41.211.212:23500",
    "124.122.9.36:8080", "124.41.211.196:30617", "125.62.198.97:83",
    "128.199.121.141:3128", "129.226.20.75:8080", "119.82.242.122:8080",
    "134.209.23.176:80", "123.25.121.152:8080", "128.199.73.231:3128",
    "128.199.67.212:8080", "128.199.84.86:3128", "128.199.202.122:3128",
    "128.199.202.122:8080", "125.59.223.27:8380", "123.27.3.246:39915",
    "125.59.153.98:8197", "120.28.57.114:80", "122.102.41.82:55783",
    "125.62.193.5:82", "132.255.23.114:999", "136.243.204.148:8080",
    "122.154.59.10:8080", "138.197.133.143:80", "138.197.157.32:3128",
    "138.197.157.32:8080", "125.162.75.179:8080", "128.199.98.29:8080",
    "134.122.17.137:8080", "138.68.240.218:3128", "138.197.32.120:3128",
    "136.169.236.23:8080", "134.209.29.120:3128", "138.68.245.146:80",
    "138.197.148.71:10087", "138.197.148.71:10000", "138.68.240.218:8080",
    "144.76.24.153:3128", "138.68.245.146:8080", "138.204.71.175:8080",
    "142.93.4.1:3128", "142.93.4.1:8080", "142.93.4.1:80", "138.68.60.8:3128",
    "140.82.60.35:3128", "149.248.51.132:80", "138.68.60.8:8080",
    "138.255.36.199:8080", "138.197.148.71:10006", "15.236.106.122:8080",
    "134.209.29.120:8080", "149.28.237.191:8080", "147.30.54.112:8080",
    "139.180.130.27:8080", "154.16.202.22:8080", "139.180.157.54:8080",
    "154.16.202.22:3128", "14.207.171.114:8080", "14.207.79.207:8080",
    "14.207.120.178:8080", "139.180.153.119:8080", "14.207.160.68:8080",
    "157.245.15.86:80", "157.230.212.58:3128", "157.245.15.86:8080",
    "140.238.15.65:3128", "157.245.15.86:3128", "140.238.16.90:3128",
    "149.28.129.224:8080", "139.162.78.109:3128", "139.162.78.109:8080",
    "149.28.154.226:8080", "139.255.160.177:8080", "144.217.101.242:3129",
    "155.138.135.165:8080", "146.88.36.43:8080", "148.217.94.54:3128",
    "159.203.44.177:3128", "159.203.2.130:80", "139.162.22.137:8080",
    "14.207.10.193:8080", "155.93.240.101:8080", "161.35.68.137:3128",
    "157.230.44.213:8080", "14.177.235.17:8080", "159.203.61.169:3128",
    "162.243.108.129:3128", "144.91.116.171:80", "161.35.50.98:3128",
    "163.172.136.226:8811", "139.228.177.168:8080", "162.243.108.129:8080",
    "154.0.15.166:46547", "159.203.61.169:8080", "14.207.74.119:8080",
    "138.99.233.6:9913", "139.255.25.83:3128", "163.172.36.42:5836",
    "161.202.226.194:80", "161.202.226.195:8123", "161.202.226.194:8123",
    "159.192.75.94:8080", "163.172.204.36:5836", "163.172.204.39:5836",
    "163.172.93.3:5836", "158.140.169.104:8181", "143.255.52.102:31158",
    "163.172.93.124:5836", "139.59.1.14:3128", "139.59.1.14:8080",
    "163.172.11.22:5836", "139.255.123.2:36466", "161.35.70.249:3128",
    "161.35.70.249:8080", "165.22.219.69:3128", "165.227.183.55:3128",
    "163.172.204.61:5836", "167.86.93.126:80", "158.69.212.254:80",
    "163.172.96.25:5836", "165.227.183.55:80", "165.227.216.105:3128",
    "165.227.183.55:8080", "167.99.54.39:8888", "162.248.243.228:8080",
    "167.99.62.83:8080", "167.71.5.83:3128", "165.227.71.60:80",
    "167.71.5.83:8080", "167.86.126.167:8080", "169.57.1.85:8123",
    "173.249.24.52:8080", "173.212.202.65:80", "172.254.124.231:3128",
    "167.86.126.167:3128", "173.249.24.52:3128", "168.205.92.105:80",
    "165.227.83.198:8080", "169.57.157.146:8123", "169.57.157.148:8123",
    "176.9.75.42:8080", "176.9.75.42:3128", "176.9.119.170:8080",
    "169.57.1.85:80", "169.57.1.84:8123", "176.9.119.170:3128",
    "169.57.157.148:80", "176.119.159.165:80", "174.138.42.112:8080",
    "163.53.185.123:8080", "167.71.221.109:3128", "178.128.206.2:80",
    "167.71.198.204:8080", "170.82.231.26:51686", "167.114.112.84:80",
    "162.243.244.206:80", "171.97.216.150:80", "178.238.232.35:5836",
    "169.57.1.84:80", "178.238.233.40:5836", "178.128.19.87:3128",
    "178.128.108.98:3128", "177.70.172.243:8080", "18.224.39.7:3128",
    "178.128.96.50:3128", "18.228.179.219:8080", "178.217.216.184:49086",
    "178.128.87.130:3128", "168.181.134.119:47848", "178.217.91.64:53281",
    "177.155.215.89:8080", "176.119.134.217:23500", "180.210.201.54:3128",
    "171.100.9.126:49163", "18.163.28.22:1080", "180.252.181.2:80",
    "180.252.181.3:80", "180.245.245.114:80", "175.100.18.45:57716",
    "176.235.99.114:30865", "178.130.106.114:8080", "180.210.201.55:3129",
    "177.129.207.23:8080", "180.210.201.57:3130", "180.250.216.242:3128",
    "182.53.127.121:8080", "180.253.111.227:8080", "180.211.191.74:53281",
    "181.30.28.14:80", "181.117.176.236:36653", "180.248.101.226:8080",
    "187.130.75.77:3130", "181.143.10.130:36535", "181.30.28.14:3128",
    "182.253.72.119:8081", "188.226.141.61:8080", "188.226.141.61:3128",
    "188.166.83.17:3128", "188.226.141.211:3128", "188.166.83.17:8080",
    "188.226.141.211:8080", "185.69.198.222:8080", "185.144.159.76:3128",
    "185.144.159.76:8080", "181.30.28.14:8080", "186.227.180.22:8080",
    "187.59.185.116:8080", "190.103.178.14:8080", "190.103.178.13:8080",
    "183.89.147.78:8080", "190.103.178.15:8080", "185.190.100.99:37399",
    "185.198.184.14:48122", "182.52.140.57:8080", "192.117.146.110:80",
    "189.5.224.17:3128", "191.96.42.80:8080", "191.96.42.80:3128",
    "187.73.11.125:8080", "192.121.232.96:80", "188.124.29.215:80",
    "193.111.254.156:3128", "188.165.16.230:3129", "191.235.65.15:8080",
    "192.41.71.221:3128", "191.252.5.250:3128", "192.41.71.204:3128",
    "194.5.206.231:8080", "192.41.13.71:3128", "185.86.134.35:8080",
    "195.154.240.249:5836", "195.123.213.85:80", "195.154.48.70:5836",
    "189.90.124.12:3128", "185.203.173.51:8080", "189.60.48.139:3128",
    "195.175.209.194:8080", "190.131.224.34:3128", "198.199.120.102:3128",
    "197.216.2.14:8080", "198.199.120.102:8080", "2.56.151.240:80",
    "198.98.54.241:8080", "198.98.50.164:8080", "199.195.248.24:8080",
    "195.138.73.54:47108", "195.154.37.9:5836", "193.85.28.234:8080",
    "195.154.112.52:5836", "194.147.27.252:23500", "195.154.33.230:5836",
    "194.8.146.167:61332", "195.55.108.26:3128", "198.199.86.11:3128",
    "198.199.86.11:8080", "200.89.174.4:3128", "197.234.35.82:53281",
    "200.89.174.4:80", "195.9.173.38:63141", "201.91.82.155:3128",
    "201.49.58.227:80", "200.60.124.109:8080", "200.69.87.4:999",
    "200.69.67.138:999", "201.150.144.102:30553", "202.166.207.58:51447",
    "202.134.180.50:80", "202.29.237.213:3128", "203.192.229.251:8080",
    "202.166.196.28:50153", "202.44.192.147:8080", "207.154.231.213:8080",
    "206.189.156.118:3128", "207.154.231.213:3128", "212.115.109.194:80",
    "203.176.135.102:54255", "207.148.25.145:8080", "202.166.220.150:32324",
    "203.150.164.102:8080", "203.202.245.62:80", "212.220.216.70:8080",
    "202.29.237.210:3128", "213.32.21.9:8080", "203.76.149.106:8080",
    "209.97.150.167:8080", "209.97.150.167:3128", "212.129.6.45:5836",
    "212.129.6.69:5836", "212.126.107.2:31475", "217.23.69.146:8080",
    "220.158.206.146:80", "212.129.6.52:5836", "23.101.2.247:81",
    "23.99.68.185:8080", "212.19.4.58:8081", "223.204.181.236:8080",
    "213.234.238.52:8080", "35.233.5.198:3128", "3.0.11.102:3128",
    "24.172.225.122:53281", "35.222.208.56:3128", "27.123.223.108:3128",
    "35.233.136.146:3128", "27.116.51.119:8080", "212.92.204.54:8080",
    "31.14.131.70:8080", "223.204.50.206:8080", "36.37.89.98:8080",
    "37.120.192.154:8080", "34.77.63.53:3128", "38.91.100.122:3128",
    "38.91.100.171:3128", "37.247.212.75:8080", "37.59.61.18:8080",
    "36.66.124.157:8080", "36.73.181.192:8080", "43.240.112.243:8080",
    "36.90.123.69:8181", "42.3.51.34:80", "36.90.249.230:8080",
    "45.32.177.4:31285", "45.76.43.163:8080", "45.76.142.110:8080",
    "41.79.197.150:8080", "45.63.6.172:8080", "45.77.151.65:8080",
    "36.89.187.193:35530", "45.77.202.207:8080", "45.76.2.34:8080",
    "46.249.36.188:3128", "46.105.191.85:80", "46.4.96.67:80",
    "45.77.65.24:3128", "45.76.162.126:8080", "45.123.26.146:53281",
    "46.4.96.137:8080", "46.4.96.137:3128", "46.148.202.194:8081",
    "41.180.64.254:80", "41.210.161.114:80", "45.77.171.50:8080",
    "45.238.38.44:8080", "5.252.161.48:8080", "5.252.161.48:3128",
    "46.4.96.87:80,", "5.189.133.231:80", "45.63.124.237:3128",
    "51.158.107.202:8811", "51.158.99.51:8811", "49.128.184.170:3128",
    "45.236.171.139:8080", "51.158.68.68:8811", "45.76.148.85:8080",
    "5.53.125.90:3128", "51.159.66.140:5836", "45.250.226.48:8080",
    "51.159.29.113:5836", "45.238.54.115:999", "45.81.108.53:8080",
    "47.21.87.110:3129", "51.159.34.123:5836", "45.33.90.184:8080",
    "52.179.231.206:80", "51.77.162.148:3128", "52.161.188.149:80",
    "51.38.127.211:8080", "51.15.182.229:5836", "54.215.33.223:3128",
    "45.233.65.41:8080", "51.15.154.111:5836", "45.71.255.122:999",
    "5.166.55.85:8080", "5.141.10.126:3130", "51.15.187.7:5836",
    "51.255.103.170:3129", "51.91.212.159:3128", "51.15.181.28:5836",
    "51.77.48.81:5836", "62.210.11.240:5836", "51.15.187.125:5836",
    "46.227.162.98:51558", "51.79.159.45:8080", "58.176.150.177:80",
    "80.240.20.183:30002", "80.187.140.26:8080", "80.187.140.26:80",
    "51.79.161.110:8080", "5.58.95.179:8080", "51.15.176.179:5836",
    "82.194.235.162:8080", "52.67.52.118:8080", "60.251.33.225:80",
    "60.251.33.224:80", "51.15.180.219:5836", "63.82.52.254:8080",
    "79.106.97.66:8080", "70.37.164.245:8080", "82.200.181.54:3128",
    "88.198.24.108:3128", "88.198.24.108:8080", "88.198.50.103:8080",
    "88.198.50.103:3128", "70.37.164.245:80", "62.210.138.179:5836",
    "80.211.29.111:3128", "63.82.52.254:3128", "79.137.44.85:3129",
    "81.144.138.35:3128", "88.99.10.248:1080", "62.210.58.169:5836",
    "71.183.100.116:80", "82.119.170.106:8080", "82.200.233.4:3128",
    "89.207.66.160:3128", "88.199.21.76:80", "91.226.35.93:53281",
    "87.76.34.207:35782", "81.162.243.249:8080", "85.198.185.26:8080",
    "88.251.72.197:8080", "92.79.65.240:8080", "94.177.247.230:8080",
    "94.177.232.56:3128", "93.174.94.80:8080", "84.232.24.201:8080",
    "88.99.10.255:1080", "91.137.140.89:8082", "94.130.179.24:8049",
    "94.130.179.24:8026", "91.133.0.229:8080", "95.179.130.83:8080",
    "95.71.30.21:8080", "95.105.116.179:8080"
]

proxy_pool = cycle(proxies)

url = 'http://docsdashboard.tech/form'

import time


def start():

    for i in proxies:
        #Get a proxy from the pool
        time.sleep(2)
        proxy = i
        counter = 0
        try:
            response = requests.get(url, proxies={"http": proxy}, timeout=2)
            counter += 1
            print(response.text)
            print("Request success %d" % (counter))
        except Exception as e:
            print(e)
            try:
                proxies.remove(i)
            except:
                print(len(proxies))
            #Most free proxies will often get connection errors. You will have retry the entire request using another proxy to work.
            #We will just skip retries as its beyond the scope of this tutorial and we are only downloading a single url
            print("Skipping. Connnection error")


import threading

p = [threading.Thread(target=start) for i in range(100)]
[x.start() for x in p]
[x.join() for x in p]


<<<<<<< HEAD
=======
"""
>>>>>>> origin/dev

tups = [(204, 1, 1527052191.579),
(26, 0, 1527052264.144),
(1, 0, 1527137578.147),
(191, 32, 1527137581.87),
(3, 0, 1527210299.654),
(116, 2, 1527210300.639),
(109, 0, 1527210598.353),
(91, 1, 1527210768.355),
(226, 1, 1527210780.103),
(1, 1, 1527214964.405),
(126, 4, 1527215726.543),
(174, 2, 1527216134.784),
(77, 0, 1527217230.469),
(183, 5, 1527217540.532),
(92, 1, 1527217934.157),
(12, 1, 1527217980.281),
(90, 3, 1527218143.285),
(88, 1, 1527218424.051),
(231, 35, 1527218460.164),
(383, 6, 1527219541.437),
(1, 1, 1527461194.067),
(274, 8, 1527461466.186),
(75, 4, 1527462157.035),
(262, 3, 1527462182.617),
(350, 1, 1527462302.673),
(205, 2, 1527463627.764),
(215, 1, 1527464275.335),
(254, 5, 1527464467.472),
(124, 1, 1527465380.491),
(295, 2, 1527465420.572),
(99, 1, 1527465664.329),
(32, 0, 1527465896.059),
(186, 2, 1527465906.583),
(1, 1, 1527466905.533),
(179, 47, 1527740240.392),
(230, 2, 1527740502.255),
(44, 6, 1527741051.082),
(234, 43, 1527741060.144),
(121, 0, 1527741360.585),
(39, 2, 1527741533.48),
(532, 6, 1527741540.191),
(160, 2, 1527741855.255),
(239, 213, 1527741900.169)]

from datetime import datetime

for i in tups:
    print(i[0], i[1], datetime.fromtimestamp(i[2]))


"""


import time

from flask import Flask, Response, stream_with_context, render_template

app = Flask(__name__)

@app.route('/stream')
def stream():
    def gen():
        try:
            i = 0
            while True:
                data = 'this is line {}'.format(i)
                i += 1
                print(data)
                yield data + '<br>'
                time.sleep(0.2)
        except GeneratorExit:
            print("closed")
        finally:
            print("gen exit")
    return Response(stream_with_context(gen()), mimetype= 'text/event-stream')


@app.route('/')
def m():
    return render_template('_test.html')


if __name__ == '__main__':
    app.run(debug=True, threaded = False, processes=1)
