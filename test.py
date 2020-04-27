import multiprocessing as mp

import time
def run(pipe):

    ds = [time.time() * time.time()] * 100000
    pipe.send(ds)
    pipe.close()

if __name__ == '__main__':

    parent_conn, child_conn = mp.Pipe()
    p = mp.Process(target = run, args = (child_conn, ))
    p.start()

    time.sleep(2)
    print(parent_conn.recv())
    print("#", end="", flush=True)

    p.join()

