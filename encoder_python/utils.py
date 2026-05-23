from functools import wraps
from time import time


def timing(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        ts = time()
        result = f(*args, **kwargs)
        te = time()
        print(f"func: {args[0].__name__} args: {args[1:], kwargs} took: {te - ts:.4} sec")
        return result
    return wrap


@timing
def benchmark(func, *args,  num=10**6, **kwargs):
    for i in range(num):
        func(*args, **kwargs)
