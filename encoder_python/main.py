import serial
import struct
import time

from config import *
from crc16 import append_crc16
from utils import print_hex


def read_all(averages=10, max_retries=5):
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        valid_reads = 0  # how many good readings so far
        failed_reads = 0
        angle_accum = 0  # accumulated sum of angle readings
        temp_accum = 0  # accumulated sum of temperature readings (deg.C)

        cmd_bytes_read_all = append_crc16(READ_REQUESTS["read_all"][0])
        ser.read(READ_DELAY_MS)

        while valid_reads < averages:
            if failed_reads > max_retries:
                break

            ser.write(cmd_bytes_read_all)
            response_header = RESPONSE_HEADERS["read_all"]
            response_data = ser.readline()  # ser.read(21)
            response_len = len(response_data)

            print("Read data:")
            print_hex(response_data, idx_padding=3, hex_idx=True)

            # does response packet look good?
            if (response_len != MAX_DATA_LEN) or (response_header != response_data[:3]):
                # print(f"Received not valid data: {response_data}")
                failed_reads += 1
                continue

            angle_raw = response_data[29:31]  # 2 bytes of angle data
            temp_raw = response_data[35:37]  # 2 bytes of temperature data

            # temp in integer hundredths of deg.C: 0x09D9 = 2521 means 25.21 C
            temp = struct.unpack(">H", temp_raw)[0]  # convert to 16-bit integer
            angle = struct.unpack(">H", angle_raw)[0]

            angle_accum += angle
            temp_accum += temp
            valid_reads += 1

        if valid_reads:
            angle_deg = DEG_PER_COUNT * (angle_accum / valid_reads)   # angle in degrees
            temp_C = temp_accum / valid_reads / 100.0                 # temp in degrees C

            time_now = time.time()
            outs = ("%0.1f, %5.3f, %5.3f" % (time_now, angle_deg, temp_C))
            print(outs)


def read_data_by_reg(averages=10):
    with serial.Serial(PORT, BAUD, timeout=TIMEOUT_SEC) as ser:
        for param, (cmd_bytes, func) in READ_REQUESTS.items():
            accum = 0

            if func is not None:
                for _ in range(averages):
                    ser.write(cmd_bytes)
                    response_data = ser.read(MAX_DATA_LEN)
                    accum += int.from_bytes(response_data[3:5], "big")

                print(f"{param} - {func(accum / averages)}")

            else:
                ser.write(cmd_bytes)
                response_data = ser.read(MAX_DATA_LEN)
                accum += int.from_bytes(response_data[3:5], "big")

                print(f"{param} - {accum}")

        param = "read_all"
        cmd_bytes, func = READ_REQUESTS[param]

        ser.write(cmd_bytes)
        response_data = ser.read(MAX_DATA_LEN)
        print_hex(response_data, 2, 3, False)


if __name__ == "__main__":
    read_data_by_reg()
    read_all()
