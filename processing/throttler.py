import asyncio
import time


class Throttle:

    def __init__(self, rpm):
        self.sem = asyncio.Semaphore(2)
        self.rpm = rpm
        self.t = time.time()
        self.counter = 1

    async def work(self, per=3):
        while True:
            await asyncio.sleep(60 * per / self.rpm)
            for i in range(per):
                self.sem.release()

    async def decrease(self):
        self.rpm -= 4.5
        self.rpm = max(self.rpm, 20)

        while (not self.sem.locked()):
            try:
                await asyncio.wait_for(self.sem.acquire(), 0.1)
            except BaseException:
                for i in range(10):
                    self.sem.release()
                break

    def increase(self):
        self.rpm += 0.25
        self.rpm = min(self.rpm, 50)

    async def acquire(self):
        self.counter += 1
        await self.sem.acquire()

    def gcount(self):
        return self.counter / (time.time() - self.t) * 60

    def reset(self):
        self.counter = 1
        self.t = time.time()
