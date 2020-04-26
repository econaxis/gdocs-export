import multiprocessing as mp

import time
def run(pipe):
    time.sleep(2)
    pipe.send(1)

if __name__ == '__main__':

    parent_conn, child_conn = mp.Pipe()
    p = mp.Process(target = run, args = (child_conn, ))
    p.start()

    while True:
        print(parent_conn.recv())
        print("#", end="", flush=True)

    p.join()

