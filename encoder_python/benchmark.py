import random

from crc16 import calc_crc16_naive, calc_crc16
from modbus import ModbusFrame
from utils import benchmark

if __name__ == '__main__':
    test_data = (0x50, 0x03, "00 11 00 01")
    arg_to_test = int.to_bytes(random.randrange(256), 2, 'big')

    frame_naive = ModbusFrame(*test_data, use_lookup_table=False)
    frame_table = ModbusFrame(*test_data, use_lookup_table=True)

    benchmark(frame_naive.build)
    benchmark(frame_table.build)

    benchmark(calc_crc16_naive, arg_to_test)
    benchmark(calc_crc16, arg_to_test)
