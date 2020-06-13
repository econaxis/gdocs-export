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

            hent = threading.Thread(target = mart)
            martt = threading.Thread(target= hen)

            hent.start()
            martt.start()

            hent.join()
            martt.join()


            import time
            time.sleep(30)


main()
