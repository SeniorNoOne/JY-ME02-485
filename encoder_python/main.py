import datetime
import os
import serial
import struct
import time

from crc16_modbus import calc_crc16_naive

max_counts = 32768                   # max number of angle counts from 15-bit sensor
max_rot = 32767                      # max number of revolutions (15-bit), MSB defines direction
deg_per_count = 360.0 / max_counts   # angular scale factor of sensor

# COM port setup
port = "COM9"
baudrate = 9600
data_len = 50

# JY-ME02-485 typical requests
cmd_bytes_request = {
    "angle": (bytes.fromhex("50 03 00 11 00 01 D9 8E"), lambda x: x * deg_per_count),
    "rot": (bytes.fromhex("50 03 00 12 00 01 29 8E"), lambda x: x if x < max_rot else x - 2 ** 16),
    "angle_vel": (bytes.fromhex("50 03 00 13 00 01 78 4E"),
                  lambda x: x if x < max_rot else x - 2 ** 16),
    "temp": (bytes.fromhex("50 03 00 14 00 01 C9 8F"), lambda x: x / 100),

    "read_all": (bytes.fromhex(f"50 03 00 00 {hex(data_len)[2:]}"), lambda x: hex(int(x))),
}

# JY-ME02-485 typical response headers
cmd_bytes_response = {
    "angle": None,
    "rot": None,
    "angle_vel": None,
    "temp": None,

    "read_all": bytes.fromhex('50 03 40'),
}


def format_hex(bytes_data, formated_byte_len=2, idx_padding=0, hex_idx=True):
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


def read_all(averages=10):
    f = file_logging()

    with serial.Serial(port, baudrate, timeout=0.1) as ser:
        ser.read(200)

        while True:
            angle_accum = 0        # accumulated sum of angle readings
            temp_accum = 0         # accumulated sum of temperature readings (deg.C)
            valid_reads = 0        # how many good readings so far

            cmd_bytes_read_all = cmd_bytes_request["read_all"][0]

            while valid_reads < averages:
                ser.write(cmd_bytes_read_all)
                response_header = cmd_bytes_response["read_all"]
                response_data = ser.read(data_len)
                response_len = len(response_data)

                print(f"Read data {response_data}")

                # does response packet look good?
                if (response_len != data_len) or (response_data[:3] != response_header):
                    first_three = response_data[:4].hex()
                    outs = ("# Receive error: %s\n" % first_three)
                    print(outs)
                    f.write(outs)
                    ser.read(200)  # clear out any bad data in receive buffer
                    continue

                angle_raw = response_data[29:31]        # 2 bytes of angle data
                temp_raw = response_data[35:37]         # 2 bytes of temperature data

                angle = struct.unpack('>H', angle_raw)[0]      # convert to 16-bit integer
                if angle > (3 * max_counts) / 4:                       # put split at -90deg
                    angle = angle - max_counts                         # redundant

                # temp in integer hundredths of deg.C: 0x09D9 = 2521 means 25.21 C
                temp = struct.unpack('>H', temp_raw)[0]        # convert to 16-bit integer

                angle_accum += angle
                temp_accum += temp
                valid_reads += 1

            angle_deg = deg_per_count * (angle_accum / valid_reads)   # angle in degrees
            temp_C = temp_accum / valid_reads / 100.0                 # temp in degrees C

            time_now = time.time()
            outs = ("%0.1f, %5.3f, %5.3f" % (time_now, angle_deg, temp_C))
            print(outs)
            f.write(outs + '\n')


def read_data_by_reg(averages=10):
    with serial.Serial(port, baudrate, timeout=0.1) as ser:
        for param, (cmd_bytes, func) in cmd_bytes_request.items():
            accum = 0

            for _ in range(averages):
                ser.write(cmd_bytes)
                response_data = ser.read(data_len)
                accum += int.from_bytes(response_data[3:5], "big")

            print(f"{param} - {func(accum / averages)}")

        param = "read_all"
        cmd_bytes, func = cmd_bytes_request[param]

        ser.write(cmd_bytes)
        response_data = ser.read(data_len)
        format_hex(response_data, 2, 3, False)


if __name__ == "__main__":
    read_data_by_reg()
    read_all(averages=1)
