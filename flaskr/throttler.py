import asyncio
import sys
import random
import json
import os
import uuid
import pickle
import aiohttp
import pprint
import math
from googleapiclient.discovery import build
import pandas as pd
import iso8601
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import time

class Throttle:
    def __init__(self, rpm):
        self.sem = asyncio.Semaphore(2)
        self.rpm = rpm
        self.t = time.time()
        self.counter = 1

    async def work(self, per = 3):
        while True:
            if (self.rpm < 10):
                self.rpm = 10
                print("less 1")
                await asyncio.sleep(40)
                self.sem.release()
            else:
                print("sleeping for: ", 60*per/self.rpm)
                await asyncio.sleep(60 * per / self.rpm)
                for i in range(per):
                    print("r", end = "")
                    self.sem.release()

            print("done r")

    def decrease(self):
        self.rpm -= 5
        self.rpm = max(self.rpm, 65)
    def increase(self):
        self.rpm +=0.6
        self.rpm = min(self.rpm, 115)
    async def acquire(self):
        self.counter += 1
        await self.sem.acquire()

    def gcount(self):
        return self.counter / (time.time() - self.t) * 60
    def reset(self):
        self.counter = 1
        self.t = time.time()
