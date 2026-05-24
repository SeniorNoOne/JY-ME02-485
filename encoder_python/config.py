from modbus import ModbusFrame

MAX_COUNTS = 32768                   # max number of angle counts from 15-bit sensor
DEG_PER_COUNT = 360.0 / MAX_COUNTS   # angular scale factor of sensor

# COM port setup
PORT = "COM8"
BAUD = 9600
TIMEOUT_SEC = 0.075

# JY-ME02-485
MAX_DATA_LEN = 69
DEVICE_ID = 0x50
READ_DELAY_MS = 200
AVERAGES = 5
REGISTER_BYTE_WIDTH = 2

READ_REQUESTS = {}
WRITE_REQUESTS = {}

FUNCTION_CODES = {
    "read": "03",
    "write": "06",
}


def _encode_general(raw_val):
    options = {
        0x00: "Save config",
        0x01: "Restore defaults",
        0xFF: "Restart",
    }

    if raw_val not in options:
        raise ValueError(f"Save {raw_val} not supported, must be one of {list(options)}")
    return raw_val


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
        "single":       0x00,
        "single_turn":  0x00,  
        "multi":        0x01,
        "multi_turn":   0x01,   
        "multiple":     0x01,    
        0x00:           0x00,
        0x01:           0x01,
    }

    if raw_val not in options:
        raise ValueError(f"Mode {raw_val} not supported, must be one of {list(options)}")
    return options[raw_val]


def _encode_angular_vel_sample_time_ms(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= MAX_COUNTS - 1)):
        raise ValueError(f"Angular velocity sampling time {raw_val} not supported, "
                         f"must be in range [0...{(MAX_COUNTS - 1) / 10}]")
    return raw_val * 10


def _encode_angle(raw_val):
    if not (isinstance(raw_val, int) and (0 <= raw_val <= 360)):
        raise ValueError(f"Angle {raw_val} not supported, must be in range [0...360]")
    return int(raw_val / DEG_PER_COUNT)


def _encode_rot(raw_val):
    if not (isinstance(raw_val, int) and (-MAX_COUNTS <= raw_val <= MAX_COUNTS - 1)):
        raise ValueError(f"Angle {raw_val} not supported, must be in range "
                         f"[{-MAX_COUNTS}...{MAX_COUNTS - 1}]")
    return raw_val + MAX_COUNTS * 2 if raw_val < 0 else raw_val


def _encode_rot_dir(raw_val):
    """
    Direction is determined looking from behind the encoder where the shaft if not exposed
    """
    options = {
        "cw":   0x00,
        "ccw":  0x01,
        "acw":  0x01,
        0x00:   0x00,
        0x01:   0x01,
    }

    if raw_val not in options:
        raise ValueError(f"Rotation direction {raw_val} not supported, "
                         f"must be one of {list(options)}")
    return options[raw_val]


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

    "general": {
        "addr": "00 00",
        "write": {"data": None, "parser": _encode_general, "dynamic": True},
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
        "write": {"data": None, "parser": _encode_mode, "dynamic": True},
    },

    # measurement registers (read/write)
    "angle": {
        "addr": "00 11",
        "read": {"data": 0x01, "parser": lambda x: x * DEG_PER_COUNT},
        "write": {"data": None, "parser": _encode_angle, "dynamic": True},
    },

    "rot": {
        "addr": "00 12",
        "read": {
            "data": 0x01,
            "parser": lambda x: int(x) if x < MAX_COUNTS else int(x - MAX_COUNTS * 2)
        },
        "write": {"data": None, "parser": _encode_rot, "dynamic": True},
    },

    "rot_dir": {
        "addr": "00 15",
        "read": {"data": 0x01, "parser": None, "dynamic": True},
        "write": {"data": None, "parser": _encode_rot_dir, "dynamic": True},
    },

    "angular_vel_sample_time_ms": {
        "addr": "00 17",
        "read": {"data": 0x01, "parser": lambda x: int(x / 10), "dynamic": True},
        "write": {"data": None, "parser": _encode_angular_vel_sample_time_ms, "dynamic": True},
    },

    # measurement registers (read only)
    "temp": {
        "addr": "00 14",
        "read": {"data": 0x01, "parser": lambda x: x / 100},
    },

    "angular_vel": {
        "addr": "00 13",
        "read": {"data": 0x01, "parser": lambda x: x if x < MAX_COUNTS else x - MAX_COUNTS * 2},
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
        dynamic = cfg["write"]["dynamic"]

        if data is None:
            frame = ModbusFrame(DEVICE_ID, FUNCTION_CODES["write"], addr).build(False)
        else:
            frame = ModbusFrame(DEVICE_ID, FUNCTION_CODES["write"], addr, (data, 2)).build()
        WRITE_REQUESTS[command] = (frame, parser, dynamic)

# JY-ME02-485 typical response headers
RESPONSE_HEADERS = {
    "angle": None,
    "rot": None,
    "angle_vel": None,
    "temp": None,

    # length was removed, since length of the response depends on request
    "read_all": bytes.fromhex("50 03"),
}
