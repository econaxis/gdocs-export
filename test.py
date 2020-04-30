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





asyncio.run(main())
