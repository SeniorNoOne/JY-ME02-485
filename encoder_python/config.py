from modbus import ModbusFrame

MAX_COUNTS = 32767                   # max number of angle counts from 15-bit sensor
DEG_PER_COUNT = 360.0 / MAX_COUNTS   # angular scale factor of sensor

# COM port setup
PORT = "COM9"
BAUD = 9600
TIMEOUT_SEC = 0.05

# JY-ME02-485
MAX_DATA_LEN = 69
DEVICE_ID = 0x50
READ_DELAY_MS = 200

FUNCTION_CODES = {
    "read": "03",
    "write": "06",
}

COMMANDS = {
    # for read operations data key means register count to read
    # for write operations it reflects data to be writen in reg (always 2 bytes)
    # unlock command to be able to use config registers
    "unlock":           {"func": "write", "addr": "00 69", "data": 0x01, "parser": None},

    # config registers (read/write, no parser needed)
    "baud":             {"func": "read", "addr": "00 04", "data": 0x01, "parser": None},
    "address":          {"func": "read", "addr": "00 1A", "data": 0x01, "parser": None},
    "mode":             {"func": "read", "addr": "00 10", "data": 0x01, "parser": None},
    "angular_vel_sr":   {"func": "read", "addr": "00 17", "data": 0x01, "parser": None},

    # bulk read
    "read_all":         {"func": "read", "addr": "00 04", "data": 0x24, "parser": None},

    # measurement registers (read only)
    "angle": {
        "func": "read",
        "addr": "00 11",
        "data": 0x01,
        "parser": lambda x: x * DEG_PER_COUNT
    },
    "rot": {
        "func": "read",
        "addr": "00 12",
        "data": 0x01,
        "parser": lambda x: x if x < MAX_COUNTS else x - 2 ** 16
    },
    "temp": {
        "func": "read",
        "addr": "00 14",
        "data": 0x01,
        "parser": lambda x: x / 100
    },
    "rot_dir": {
        "func": "read",
        "addr": "00 15",
        "data": 0x01,
        "parser": None
    },
    "angular_vel": {
        "func": "read",
        "addr": "00 13",
        "data": 0x01,
        "parser": lambda x: x if x < MAX_COUNTS else x - 2 ** 16
    },
}

READ_REQUESTS = {}

for command, vals in COMMANDS.items():
    if vals["func"] != "read":
        continue

    frame = ModbusFrame(
        DEVICE_ID,
        FUNCTION_CODES["read"],
        vals["addr"],
        (vals["data"], 2)
    ).build()

    READ_REQUESTS[command] = (frame, vals["parser"])


# JY-ME02-485 typical response headers
RESPONSE_HEADERS = {
    "angle": None,
    "rot": None,
    "angle_vel": None,
    "temp": None,

    # length was removed, since length of the response depends on request
    "read_all": bytes.fromhex("50 03"),
}
