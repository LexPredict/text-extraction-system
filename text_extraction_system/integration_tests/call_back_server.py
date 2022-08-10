# -*- coding: utf-8 -*-

import logging
import socket
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from time import sleep, time
from typing import Callable, Dict, Any, List

from integration_tests.testing_config import test_settings
from integration_tests.utils import SingletonMeta

log = logging.getLogger(__name__)


class MockServerRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.server.request_received = True

        try:
            log.info(f'POST request received to the test call-back server: '
                     f'{self.path}\n{self.request}')
            content_len = int(self.headers.get('content-length', 0))
            if hasattr(self.server, "test_func") and callable(getattr(self.server, "test_func")):
                self.server.test_func(self.rfile.read(content_len), self.headers)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Thanks!')
        except Exception as e:
            self.server.test_problem = e

        self.server.__shutdown_request = True


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('0.0.0.0', 0))
    address, port = s.getsockname()
    s.close()
    return port


class DocumentCallbackServer(metaclass=SingletonMeta):
    def __init__(self,
                 bind_host: str = test_settings.call_back_server_bind_host,
                 bind_port: int = test_settings.call_back_server_bind_port,
                 start: bool = True) -> None:
        super().__init__()
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.mock_server = HTTPServer((self.bind_host, self.bind_port), MockServerRequestHandler)
        self.mock_server.test_func = lambda rfile, headers: \
            log.info('Text extraction results are ready...')
        self.mock_server.request_received = False
        self.mock_server.test_problem = None
        self.mock_server_thread = Thread(target=self.mock_server.serve_forever)
        self.mock_server_thread.setDaemon(True)
        if start:
            self.start()

    def start(self):
        self.mock_server_thread.start()
        log.info(f'Started test call-back server at {self.bind_host}:{self.bind_port}')

    def stop(self):
        self.mock_server.shutdown()

    @contextmanager
    def prepare_test_results(self, timeout_sec: int):
        if self.mock_server_thread.is_alive() and not self.mock_server.request_received:
            log.info(f'Waiting {timeout_sec} seconds for call back...')
        start_time = time()
        while self.mock_server_thread.is_alive() \
                and not self.mock_server.request_received \
                and time() - start_time < timeout_sec:
            sleep(0.5)
        try:
            yield
        finally:
            if not self.mock_server.request_received:
                raise TimeoutError()
            self.mock_server.request_received = False
            if self.mock_server.test_problem is not None:
                raise Exception() from self.mock_server.test_problem
            self.mock_server.test_problem = None
            log.info(f'Done in {time() - start_time} seconds')

    def wait_for_test_results(self,
                              timeout_sec: int,
                              assert_func: Callable[[Any, Dict[str, Any], ], None],
                              assert_func_args: List):
        with self.prepare_test_results(timeout_sec=timeout_sec):
            assert_func(*assert_func_args)
