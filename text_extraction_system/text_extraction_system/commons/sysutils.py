import resource
import sys


def increase_recursion_limit():
    current_val = resource.getrlimit(resource.RLIMIT_STACK)[0]
    try:
        resource.setrlimit(resource.RLIMIT_STACK, (current_val, -1))
    except:
        resource.setrlimit(resource.RLIMIT_STACK, (current_val, current_val))
    sys.setrecursionlimit(50000)
