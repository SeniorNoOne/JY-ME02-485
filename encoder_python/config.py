from modbus import ModbusFrame

MAX_COUNTS = 32768                   # max number of angle counts from 15-bit sensor
DEG_PER_COUNT = 360.0 / MAX_COUNTS   # angular scale factor of sensor

# COM port setup
PORT = "COM9"
BAUD = 9600
TIMEOUT_SEC = 0.02

# JY-ME02-485
MAX_DATA_LEN = 69
DEVICE_ID = 0x50
READ_DELAY_MS = 200

READ_REQUESTS = {}
WRITE_REQUESTS = {}

FUNCTION_CODES = {
    "read": "03",
    "write": "06",
}


def _encode_baud(raw_val):
    options = {
        4800: 0x01, 9600: 0x02, 19200: 0x03, 38400: 0x04,
        57600: 0x05, 115200: 0x06, 230400: 0x07
    }

    if raw_val not in options:
        raise ValueError(f"Baud {raw_val} not supported, must be one of {list(options)}")
    return options[raw_val]


def _encode_address(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= 127)):
        raise ValueError(f"Address {raw_val} not supported, must be in range [0...127]")
    return raw_val


def _encode_mode(raw_val):
    options = {
        0x00: "Single turn mode",
        0x01: "Multiple turn mode",
    }

    if raw_val not in options:
        raise ValueError(f"Mode {raw_val} not supported, must be one of {list(options)}")
    return options[raw_val]


def _encode_angular_vel_sr(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= MAX_COUNTS - 1)):
        raise ValueError(f"Angular velocity sampling time {raw_val} not supported, "
                         f"must be in range [0...{MAX_COUNTS - 1}]")
    return raw_val


def _encode_angle(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= 360)):
        raise ValueError(f"Angle {raw_val} not supported, must be one of [0...360]")
    return raw_val


def _encode_rot(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= MAX_COUNTS)):
        raise ValueError(f"Angle {raw_val} not supported, must be one of f[0...{MAX_COUNTS - 1}]")
    return raw_val


def _encode_rot_dir(raw_val):
    options = {
        0x00: "Clockwise",
        0x01: "Anticlockwise",
    }

    if raw_val not in options:
        raise ValueError(f"Rotation direction {raw_val} not supported, "
                         f"must be one of {list(options)}")
    return raw_val


COMMANDS = {
    # for read operations data key means register count to read
    # for write operations it reflects data to be written in reg (always 2 bytes)
    # dynamic=True means data is supplied at call time, not prebuilt
    # parser under "write" is an encoder: physical value -> raw register value
    # parser under "read" in a decoder: raw register value -> physical value
    # unlock command to be able to use config registers
    "unlock": {
        "addr": "00 69",
        "write": {"data": 0xB588, "parser": None, "dynamic": False},
    },

    # bulk read
    "all": {
        "addr": "00 04",
        "read": {"data": 0x24, "parser": None},
    },

    # config registers (read/write, no parser needed)
    "baud": {
        "addr": "00 04",
        "read": {"data": 0x01, "parser": None},
        "write": {"data": None, "parser": _encode_baud, "dynamic": True},
    },

    "address": {
        "addr": "00 1A",
        "read": {"data": 0x01, "parser": None},
        "write": {"data": None, "parser": _encode_address, "dynamic": True},
    },

    "mode": {
        "addr": "00 10",
        "read": {"data": 0x01, "parser": None, "dynamic": True},
        "write": {"data": None, "parser": _encode_address, "dynamic": True},
    },

    # measurement registers (read/write)
    "angle": {
        "addr": "00 11",
        "read": {"data": 0x01, "parser": lambda x: x * DEG_PER_COUNT},
        "write": {"data": None, "parser": _encode_angle, "dynamic": True},
    },

    "rot": {
        "addr": "00 12",
        "read": {"data": 0x01, "parser": lambda x: x if x < MAX_COUNTS else x - MAX_COUNTS},
        "write": {"data": None, "parser": _encode_rot, "dynamic": True},
    },

    "rot_dir": {
        "addr": "00 15",
        "read": {"data": 0x01, "parser": None, "dynamic": True},
        "write": {"data": None, "parser": _encode_rot_dir, "dynamic": True},
    },

    "angular_vel_sr": {
        "addr": "00 17",
        "read": {"data": 0x01, "parser": None, "dynamic": True},
        "write": {"data": None, "parser": _encode_angular_vel_sr, "dynamic": True},
    },

    # measurement registers (read only)
    "temp": {
        "addr": "00 14",
        "read": {"data": 0x01, "parser": lambda x: x / 100},
    },

    "angular_vel": {
        "addr": "00 13",
        "read": {"data": 0x01, "parser": lambda x: x if x < MAX_COUNTS else x - MAX_COUNTS},
    },
}

for command, cfg in COMMANDS.items():
    addr = cfg["addr"]

    if "read" in cfg:
        data = cfg["read"]["data"]
        parser = cfg["read"]["parser"]
        frame = ModbusFrame(DEVICE_ID, FUNCTION_CODES["read"], addr, (data, 2)).build()
        READ_REQUESTS[command] = (frame, parser)

    if "write" in cfg:
        data = cfg["write"]["data"]
        parser = cfg["write"]["parser"]

        if data is None:
            frame = ModbusFrame(DEVICE_ID, FUNCTION_CODES["write"], addr).build()
        else:
            frame = ModbusFrame(DEVICE_ID, FUNCTION_CODES["write"], addr, (data, 2)).build()
        WRITE_REQUESTS[command] = (frame, parser)

# JY-ME02-485 typical response headers
RESPONSE_HEADERS = {
    "angle": None,
    "rot": None,
    "angle_vel": None,
    "temp": None,

    # length was removed, since length of the response depends on request
    "read_all": bytes.fromhex("50 03"),
}
