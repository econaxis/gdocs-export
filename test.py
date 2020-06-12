import dsds
from processing import get_files
from processing import gdoc
from configlog import tracer
import subprocess


def main():
    for threads in range(2, 6):
        for workers in range(3, 8):
            gdoc.threads = threads
            get_files.workerInstances = workers
            with tracer.span("LARGE TEST threads: {} ;; workers {}".format(threads, workers)):
                print("outside threads: {} ;; workers {}".format(threads, workers))
                subprocess.run(['python', 'dsds.py', str(threads), str(workers)])
main()
