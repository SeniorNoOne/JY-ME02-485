import random
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


def generate_crc16_table():
    table = []

    for i in range(256):
        crc = (
            i)

        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

        table.append(crc & 0xFFFF)

    return table


def calc_crc16_naive(data):
    crc = 0xFFFF

    for byte in data:
        crc ^= byte

        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    return crc & 0xFFFF


def calc_crc16(data):
    crc = 0xFFFF

    for byte in data:
        crc = (crc >> 8) ^ crc16_table[(crc ^ byte) & 0xFF]

    return crc & 0xFFFF


if __name__ == '__main__':
    crc16_table = generate_crc16_table()
    arg_to_test = int.to_bytes(crc16_table[random.randrange(256)], 2, 'big')

    benchmark(calc_crc16_naive, arg_to_test)
    benchmark(calc_crc16, arg_to_test)
