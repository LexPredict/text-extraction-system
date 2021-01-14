import socket
import time
from contextlib import contextmanager
from typing import Callable


@contextmanager
def get_lock(name,
             sleep_time_sec: float = 0.5,
             wait_required_listener: Callable = None):
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    had_to_wait_notified: bool = False
    while True:
        try:
            lock_socket.bind('\0' + name)
            yield
            break
        except socket.error:
            if not had_to_wait_notified and wait_required_listener is not None:
                had_to_wait_notified = True
                wait_required_listener()
            time.sleep(sleep_time_sec)
