from ..escape_utils import get_valid_fn


def test_get_valid_fn1():
    s = '/etc/passwd'
    expected = '_etc_passwd'
    assert get_valid_fn(s) == expected


def test_get_valid_fn2():
    s = '../../../etc/passwd'
    expected = '_________etc_passwd'
    assert get_valid_fn(s) == expected


def test_get_valid_fn3():
    s = '..//../../hello worl(;""""""".,,,.\\ddd.pdf'
    expected = '__________hello_worl_______________ddd.pdf'
    assert get_valid_fn(s) == expected
