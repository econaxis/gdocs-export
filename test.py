import dsds
from processing import get_files
from processing import gdoc
from configlog import tracer
import subprocess

def run(threads, workers, mart):
    with tracer.span("LARGE TEST threads: {} ;; workers {}".format(threads, workers)):
        if mart:
            subprocess.run(['python3.8', 'dsds.py', '-t {}'.format(str(threads)), '-w {}'.format( str(workers)), '-m'])
        else:
            subprocess.run(['python3.8', 'dsds.py', '-t {}'.format(str(threads)), '-w {}'.format( str(workers))])

def main():
    for threads in range(2, 3):
        for workers in range(3, 6):
            if threads > workers:
                continue
            import threading
            
            mart = lambda: run(threads, workers, False)
            hen = lambda: run(threads, workers, True)

            hent = [threading.Thread(target = mart) for i in range(3)]
            martt = [threading.Thread(target= hen) for i in range(3) ]

            [x.start() for x in hent]
            [x.start() for x in martt]
            [x.join() for x in hent]
            [x.join() for x in martt]


            import time
            time.sleep(30)


main()
