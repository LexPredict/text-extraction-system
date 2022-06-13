from integration_tests.call_back_server import DocumentCallbackServer


def pytest_configure(config):
    # start singleton DocumentCallbackServer
    DocumentCallbackServer()


def pytest_unconfigure(config):
    # stop singleton DocumentCallbackServer
    DocumentCallbackServer().stop()
