import serial
import struct
import time

from modbus import ModbusFrame
from crc16 import append_crc16
from utils import print_hex

max_counts = 32768                   # max number of angle counts from 15-bit sensor
max_rot = 32767                      # max number of revolutions (15-bit), MSB defines direction
deg_per_count = 360.0 / max_counts   # angular scale factor of sensor

# COM port setup
# need to adjust these variables
port = "COM9"
baudrate = 9600
data_len = 69

# JY-ME02-485 typical requests
device_id = 0x50
register_count = (1, 2)
read_len = (1, 2)  # read length and number of bytes required to represent it

function_codes = {
    "read": "03",
    "write": "06",
}

registers = {
    "baud": "00 04",
    "address": "00 1A",
    "mode": "00 10",
    "angular_vel_sampling_time": "00 17",
    "angle": "00 11",
    "rot": "00 12",
    "temp": "00 14",
    "rot_dir": "00 15",
    "angular_vel": "00 13",
}

response_parsers = {
    "baud": None,
    "address": None,
    "mode": None,
    "angular_vel_sampling_time": None,
    "angle": lambda x: x * deg_per_count,
    "rot": lambda x: x if x < max_rot else x - 2 ** 16,
    "temp": lambda x: x / 100,
    "rot_dir": None,
    "angular_vel": lambda x: x if x < max_rot else x - 2 ** 16,
}

read_requests = {
    param: (ModbusFrame(device_id, function_codes["read"],
                        registers[param], register_count).build(),
            response_parsers[param]) for param in registers
}

# JY-ME02-485 typical response headers
response_headers = {
    "angle": None,
    "rot": None,
    "angle_vel": None,
    "temp": None,

    # length was removed, since length of the response depends on request
    "read_all": bytes.fromhex('50 03'),
}


def read_all(averages=10, max_retries=5):
    with serial.Serial(port, baudrate, timeout=0.1) as ser:
        valid_reads = 0  # how many good readings so far
        failed_reads = 0
        angle_accum = 0  # accumulated sum of angle readings
        temp_accum = 0  # accumulated sum of temperature readings (deg.C)

        cmd_bytes_read_all = append_crc16(read_requests["read_all"][0])
        ser.read(200)

        while valid_reads < averages:
            if failed_reads > max_retries:
                break

            ser.write(cmd_bytes_read_all)
            response_header = response_headers["read_all"]
            response_data = ser.readline()  # ser.read(21)
            response_len = len(response_data)

            print("Read data:")
            print_hex(response_data, idx_padding=3, hex_idx=True)

            # does response packet look good?
            if (response_len != data_len) or (response_header != response_data[:3]):
                # print(f"Received not valid data: {response_data}")
                failed_reads += 1
                continue

            angle_raw = response_data[29:31]  # 2 bytes of angle data
            temp_raw = response_data[35:37]  # 2 bytes of temperature data

            # temp in integer hundredths of deg.C: 0x09D9 = 2521 means 25.21 C
            temp = struct.unpack('>H', temp_raw)[0]  # convert to 16-bit integer
            angle = struct.unpack('>H', angle_raw)[0]

            angle_accum += angle
            temp_accum += temp
            valid_reads += 1

        if valid_reads:
            angle_deg = deg_per_count * (angle_accum / valid_reads)   # angle in degrees
            temp_C = temp_accum / valid_reads / 100.0                 # temp in degrees C

            time_now = time.time()
            outs = ("%0.1f, %5.3f, %5.3f" % (time_now, angle_deg, temp_C))
            print(outs)


def read_data_by_reg(averages=10):
    with serial.Serial(port, baudrate, timeout=0.1) as ser:
        for param, (cmd_bytes, func) in read_requests.items():
            accum = 0

            for _ in range(averages):
                ser.write(cmd_bytes)
                response_data = ser.read(data_len)
                accum += int.from_bytes(response_data[3:5], "big")

            print(f"{param} - {func(accum / averages)}")

        param = "read_all"
        cmd_bytes, func = read_requests[param]

        ser.write(cmd_bytes)
        response_data = ser.read(data_len)
        print_hex(response_data, 2, 3, False)


if __name__ == "__main__":
    read_data_by_reg()
    read_all()
