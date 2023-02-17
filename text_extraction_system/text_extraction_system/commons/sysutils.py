import resource
import sys


def increase_recursion_limit():
    resource.setrlimit(resource.RLIMIT_STACK, (10 * (2 ** 20), 10 * (2 ** 20)))
    sys.setrecursionlimit(50000)
