import time
from multiprocessing import Process

from text_extraction_system.locking.socket_lock import get_lock


def test_socket_lock():
    had_to_wait: bool = False

    def do_with_lock():
        with get_lock('my_lock'):
            print('First method got the lock. Sleeping 5 seconds.')
            time.sleep(5)
            print('First method exit.')

    def print_lock_wait():
        nonlocal had_to_wait
        had_to_wait = True
        print('Second method had to wait for the lock.')

    Process(target=do_with_lock).start()
    time.sleep(0.5)

    with get_lock('my_lock', wait_required_listener=print_lock_wait):
        print('Second method got the lock and exited.')
    assert had_to_wait
