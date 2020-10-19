# -*- coding: utf-8 -*-

import socket
from cgi import parse_header, parse_multipart
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from time import sleep, time
from typing import Callable, Dict, List


class MockServerRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.server.request_received = True

        try:
            print(self.path)
            print(self.request)

            print(self.headers)
            ctype, pdict = parse_header(self.headers['content-type'])

            if 'boundary' in pdict:
                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")

            print("ctype", ctype, ctype == 'application/octet-stream')
            print(pdict)
            if ctype == 'multipart/form-data':
                multipart_data = parse_multipart(self.rfile, pdict)
                self.server.test_func(multipart_data)
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Where is the document? '
                                 b'It should be multipart/form-data with the document in "file" field.')
                raise Exception(f'Wrong call back request received:\n{self.request}')
        except Exception as e:
            self.server.test_problem = e

        self.server.__shutdown_request = True


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('0.0.0.0', 0))
    address, port = s.getsockname()
    s.close()
    return port


class DocumentCallbackServer(object):

    def __init__(self, bind_host: str, bind_port: int, test_func: Callable[[Dict[str, List], ], None],
                 start: bool = True) -> None:
        super().__init__()
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.mock_server = HTTPServer((self.bind_host, self.bind_port), MockServerRequestHandler)
        self.mock_server.test_func = test_func
        self.mock_server.request_received = False
        self.mock_server.test_problem = None
        self.mock_server_thread = Thread(target=self.mock_server.serve_forever)
        self.mock_server_thread.setDaemon(True)
        if start:
            self.start()

    def start(self):
        self.mock_server_thread.start()
        print(f'Started mock server at {self.bind_host}:{self.bind_port}')

    def stop(self):
        self.mock_server.shutdown()

    def wait_for_test_results(self, timeout_sec: int):
        if self.mock_server_thread.is_alive() \
                and not self.mock_server.request_received:
            print(f'Waiting {timeout_sec} seconds for call back...')
        start_time = time()
        while self.mock_server_thread.is_alive() \
                and not self.mock_server.request_received \
                and time() - start_time < timeout_sec:
            sleep(0.5)
        self.mock_server.shutdown()
        if not self.mock_server.request_received:
            raise TimeoutError()
        elif self.mock_server.test_problem is not None:
            raise Exception() from self.mock_server.test_problem
        else:
            print(f'Done in {time() - start_time} seconds')
