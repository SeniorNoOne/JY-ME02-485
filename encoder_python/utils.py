import datetime
import os

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


def print_hex(bytes_data, formated_byte_len=2, idx_padding=0, hex_idx=True):
    # formated_byte_len
    # 0x00 it takes 4 chars to formax HEX number without 0x part
    index_row = ""
    data_row = ""

    for idx_, byte in enumerate(bytes_data):
        idx_formated = 0 if idx_ - idx_padding < 0 else idx_ - idx_padding
        index_row += f"{idx_formated:>{formated_byte_len}{'X' if hex_idx else 'd'}} "
        data_row += f"{byte:>{formated_byte_len}X} "

    print(index_row)
    print(data_row)


def file_logging():
    LOGDIR = r"./logdir"
    LOGFILE = "encoder_data.csv"
    VERSION = "JY-ME02"
    CSV_HEADER = "time, angle, rot, degC"

    dt_string = datetime.datetime.today().strftime('%Y-%m-%d_%H%M%S_')
    file_name_out = os.path.join(LOGDIR, (dt_string + LOGFILE))

    print("Writing data to %s" % file_name_out)

    f = open(file_name_out, 'w')  # open log file
    f.write("%s\n" % CSV_HEADER)
    f.write("# %s\n" % VERSION)

    return f
