"""Some utility functions."""
__author__ = "Michael Cohen <scudette@gmail.com>"


def SmartStr(string, encoding="utf8"):
    """Forces the string to be an encoded byte string."""
    if isinstance(string, str):
        return string.encode(encoding, "ignore")
    if isinstance(string, bytes):
        return string
    if hasattr(string, "__bytes__"):
        return string.__bytes__()
    return str(string).encode(encoding)


def SmartUnicode(string, encoding="utf8"):
    """Forces the string into a unicode object."""
    if isinstance(string, bytes):
        return string.decode(encoding)
    return str(string)


def AssertStr(string):
    if type(string) is not bytes:
        raise RuntimeError("String must be bytes.")


def AssertUnicode(string):
    if type(string) is not str:
        raise RuntimeError("String must be unicode.")


def asList(a, b):
    a_islist = isinstance(a, list)
    b_islist = isinstance(b, list)

    if a is None:
        return b if b_islist else [b]
    elif b is None:
        return a if a_islist else [a]
    else:
        if a_islist and b_islist:
            a.extend(b)
            return a
        elif b_islist:
            b.append(a)
            return b
        elif a_islist:
            a.append(b)
            return a
        else:
            return [a, b]
