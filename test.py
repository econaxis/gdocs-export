import asyncio

sem = None

async def task():
    while True:
        print("before acq")
        await sem.acquire()
        print('after acq')
async def rls():
    while True:
        await asyncio.sleep(3)
        print("releasing")
        sem = asyncio.Semaphore(20)
        sem.release()
        print("done releasing")

async def main():
    global sem
    sem = asyncio.Semaphore(2)
    tk = asyncio.create_task(task())
    rl = asyncio.create_task(rls())

    await tk
    await rl

if __name__ == '__main__':
    asyncio.run(main())
    
