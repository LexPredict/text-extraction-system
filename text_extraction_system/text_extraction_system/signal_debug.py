import datetime
import os
import signal
import threading
import time

SIGNAL_NAMES_BY_NUM = {int(getattr(signal, sig_name)): sig_name
                       for sig_name in dir(signal)
                       if sig_name.startswith('SIG')
                       and not sig_name.startswith('SIG_')}


def receive_signal(sig_num: int, frame):
    print(f'{datetime.datetime.now().isoformat()} |  Signal: {SIGNAL_NAMES_BY_NUM[sig_num]} ({sig_num})')


if __name__ == '__main__':
    for sig_num in sorted(SIGNAL_NAMES_BY_NUM.keys()):
        if sig_num == signal.SIGKILL:
            continue
        try:
            signal.signal(sig_num, receive_signal)
            print(f'Added handler for {SIGNAL_NAMES_BY_NUM[sig_num]} ({sig_num})')
        except Exception:
            print(f'Can not add handler for {SIGNAL_NAMES_BY_NUM[sig_num]} ({sig_num})')

    print(f'PID of this process: {os.getpid()}')
    print(f'Id of this thread: {threading.current_thread().ident}')

    while True:
        time.sleep(300)
