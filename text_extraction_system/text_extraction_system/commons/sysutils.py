import resource
import sys


def increase_recursion_limit():
    if sys.platform == "darwin":
        return False
    resource.setrlimit(resource.RLIMIT_STACK, (2 ** 29, -1))
    sys.setrecursionlimit(50000)
    return True
