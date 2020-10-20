import os
import re


def get_valid_fn(s: str) -> str:
    """
    Return valid escaped filename from a string.
    Removes path separators and "..". Shortens to max 64 characters.
    Tries to keep the original extension.

    Based on the function with the same name from Django Framework.
    """
    fn, ext = os.path.splitext(str(s))
    fn, ext = [re.sub(r'(?u)[^-_\w]', '_', str(ss).strip().replace(' ', '_'))
               for ss in [fn, ext.strip('.')]]
    return fn + '.' + ext if ext else fn
