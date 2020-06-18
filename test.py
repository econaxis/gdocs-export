import dsds
import time
from processing import get_files
from processing import gdoc
from configlog import tracer
import subprocess
import random

def run(threads, workers, mart):
    time.sleep(random.uniform(10, 50))
    with tracer.span("LARGE TEST threads: {} ;; workers {}".format(threads, workers)):
        if mart:
            subprocess.run(['python3.8', 'dsds.py', '-t {}'.format(str(threads)), '-w {}'.format( str(workers)), '-m'])
        else:
            subprocess.run(['python3.8', 'dsds.py', '-t {}'.format(str(threads)), '-w {}'.format( str(workers))])

def main():
    for i in range(10):
        for threads in range(2, 3):
            for workers in range(3, 6):
                if threads > workers:
                    continue
                import threading
                
                mart = lambda: run(threads, workers, False)
                hen = lambda: run(threads, workers, True)

                hent = [threading.Thread(target = mart) for i in range(1)]
                martt = [threading.Thread(target= hen) for i in range(1)]

                [x.start() for x in hent]
                [x.start() for x in martt]
                [x.join() for x in hent]
                [x.join() for x in martt]

                print("sleeping")
                time.sleep(15)


main()
