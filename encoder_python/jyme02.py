import serial
from types import MappingProxyType

import config as cfg
from modbus import ModbusFrame


# TODO:
#  - add write benchmark function, but note that id DEVICE_ID is changed in runtime,
#    then COMMANDS and all other config dicts should be reevaluated
#  - expose print_cmd flag to CLI


class JYME02:
    def __init__(self, com,
                 device_id=cfg.DEFAULT_DEVICE_ID,
                 baud=cfg.DEFAULT_BAUD,
                 timeout=cfg.DEFAULT_TIMEOUT_SEC,
                 averages=cfg.DEFAULT_AVERAGES,
                 func_codes=None,
                 commands=None):
        # Serial specific
        self.com = cfg.validate_com(com)
        self.baud = cfg.validate_baud(baud, return_raw=True)
        self.timeout = cfg.validate_timeout(timeout)
        self.averages = cfg.validate_averages(averages)

        # Modbus specific
        self._register_byte_width = cfg.DEFAULT_REGISTER_BYTE_WIDTH
        self._max_data_len = cfg.DEFAULT_MAX_DATA_LEN
        self._func_codes = (MappingProxyType(func_codes) if func_codes is not None
                            else cfg.FUNCTION_CODES)
        self._commands = MappingProxyType(commands) if commands is not None else cfg.COMMANDS
        self._read_commands = {}
        self._write_commands = {}

        # Validating device_id and building requests via setter
        self.device_id = device_id

    @property
    def device_id(self):
        return self._device_id

    @property
    def register_byte_width(self):
        return self._register_byte_width

    @property
    def max_data_len(self):
        return self._max_data_len

    @property
    def func_codes(self):
        return self._func_codes

    @property
    def commands(self):
        return self._commands

    @property
    def read_commands(self):
        return self._read_commands

    @property
    def write_commands(self):
        return self._write_commands

    @device_id.setter
    def device_id(self, device_id):
        self._device_id = cfg.validate_device_id(device_id)
        self._build_requests()

    def _build_requests(self):
        for command, conf in self._commands.items():
            addr = conf["addr"]

            if "read" in conf:
                data = conf["read"]["data"]
                parser = conf["read"]["parser"]
                frame = ModbusFrame(self._device_id,
                                    self._func_codes["read"],
                                    addr,
                                    (data, 2))
                self._read_commands[command] = (frame.build(), parser)

            if "write" in conf:
                data = conf["write"]["data"]
                parser = conf["write"]["parser"]
                dynamic = conf["write"]["dynamic"]

                if dynamic:
                    frame = ModbusFrame(self._device_id, self._func_codes["write"], addr)
                    self._write_commands[command] = (frame.build(add_crc=False), parser, dynamic)
                else:
                    frame = ModbusFrame(self._device_id,
                                        self._func_codes["write"],
                                        addr,
                                        (data, 2))
                    self._write_commands[command] = (frame.build(), parser, dynamic)

    def _read_register(self, cmd_bytes, averages):
        accum = 0

        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            for _ in range(averages):
                ser.write(cmd_bytes)
                response_data = ser.read(self._max_data_len)
                accum += int.from_bytes(response_data[3:5], "big")

        return accum / averages

    def read(self, command, print_cmd=False):
        cmd_bytes, parser = self._read_commands[command]

        if print_cmd:
            print(cmd_bytes.hex())

        raw = self._read_register(cmd_bytes, self.averages if parser else 1)
        return parser(raw) if parser else raw

    def _write_register(self, cmd_bytes):
        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            ser.write(cmd_bytes)
            response_data = ser.read(self._max_data_len)
        return response_data

    def write(self, command, raw_val=None, print_cmd=False):
        cmd_bytes_template, encoder, dynamic = self._write_commands[command]

        if encoder:
            data = encoder(raw_val)
        else:
            data = raw_val
        data = (data, self._register_byte_width)

        cmd_bytes = ModbusFrame(cmd_bytes_template, data).build() if dynamic else cmd_bytes_template

        if print_cmd:
            print(cmd_bytes.hex())

        raw = self._write_register(cmd_bytes)
        return raw

    def write_wrapped(self, command, raw_val=None):
        self.unlock()
        self.write(command, raw_val)
        self.save()

    def read_angle(self):
        return self.read("angle")

    def read_rot(self):
        return self.read("rot")

    def read_temp(self):
        return self.read("temp")

    def read_rot_dir(self):
        return self.read("rot_dir")

    def read_angular_vel(self):
        return self.read("angular_vel")

    def read_baud(self):
        return self.read("baud")

    def read_address(self):
        return self.read("address")

    def read_mode(self):
        return self.read("mode")

    def read_angular_vel_sample_time_ms(self):
        return self.read("angular_vel_sample_time_ms")

    def read_all(self):
        return self.read("all")

    def benchmark_read(self):
        for param in self._read_commands:
            method = getattr(self, f"read_{param}")
            if method:
                print(f"{param}: {method()}")

    def unlock(self):
        return self.write("unlock")

    def save(self):
        return self.write("general", 0x00)

    def restart(self):
        return self.write("general", 0xFF)

    def reset(self):
        return self.write("general", 0x01)

    def write_baud(self, raw_val):
        # probably requires power cycling
        self.write_wrapped("baud", raw_val)

    def write_address(self, raw_val):
        self.write_wrapped("address", raw_val)

    def write_mode(self, raw_val):
        self.write_wrapped("mode", raw_val)

    def write_angle(self, raw_val):
        self.write_wrapped("angle", raw_val)

    def write_rot(self, raw_val):
        self.write_wrapped("rot", raw_val)

    def write_rot_dir(self, raw_val):
        self.write_wrapped("rot_dir", raw_val)

    def write_angular_vel_sample_time_ms(self, raw_val):
        self.write_wrapped("angular_vel_sample_time_ms", raw_val)
