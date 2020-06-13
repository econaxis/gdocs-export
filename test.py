import dsds
from processing import get_files
from processing import gdoc
from configlog import tracer
import subprocess


def main():
    for threads in range(2, 4):
        for workers in range(3, 6):
            gdoc.threads = threads
            get_files.workerInstances = workers
            with tracer.span("LARGE TEST threads: {} ;; workers {}".format(threads, workers)):
                subprocess.run(['python3.8', 'dsds.py', '-t {}'.format(str(threads)), '-w {}'.format( str(workers)), '-m'])


main()
