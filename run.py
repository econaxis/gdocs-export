from flaskr import create_flask_serv
import configlog
import logging

logger = logging.getLogger(__name__)

import signal
from contextlib import contextmanager


@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)
    try:
        yield
    except TimeoutError:
        pass
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def raise_timeout(signum, frame):
    raise TimeoutError


app = create_flask_serv()

logger.info("create_flask_serv done")
app.logger.addHandler(configlog.syslog)
app.logger.addHandler(configlog.stream)
app.logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    pass
    #app.run(debug=True, port=4000)
