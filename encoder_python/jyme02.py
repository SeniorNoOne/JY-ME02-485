import serial

from config import FUNCTION_CODES, COMMANDS, REGISTER_BYTE_WIDTH, MAX_DATA_LEN, _encode_address
from modbus import ModbusFrame


# TODO:
#  - add write benchmark function, but note that id DEVICE_ID is changed in runtime,
#    then COMMANDS and all other config dicts should be reevaluated
#  - make generation of the config dicts via functions
#  - expose print_cmd flag to CLI


class JYME02:
    def __init__(self, com, device_id, baud=9600, timeout=0.02, averages=5,
                 register_byte_width=REGISTER_BYTE_WIDTH, max_data_len=MAX_DATA_LEN,
                 function_codes=None, commands=None):
        # Serial specific
        self.com = com
        self.baud = baud
        self.timeout = timeout
        self.averages = averages

        # Modbus specific
        self._device_id = device_id
        self._register_byte_width = register_byte_width
        self._max_data_len = max_data_len
        self._func_codes = function_codes if function_codes is not None else FUNCTION_CODES
        self._commands = commands if commands is not None else COMMANDS
        self._read_commands = {}
        self._write_commands = {}

        # Explicitly building requests
        self._build_requests()

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, device_id):
        self._device_id = _encode_address(device_id)
        self._build_requests()

    def _build_requests(self):
        for command, cfg in self._commands.items():
            addr = cfg["addr"]

            if "read" in cfg:
                data = cfg["read"]["data"]
                parser = cfg["read"]["parser"]
                frame = ModbusFrame(self._device_id,
                                    self._func_codes["read"],
                                    addr,
                                    data
                                    )
                self._read_commands[command] = (frame.build(), parser)

            if "write" in cfg:
                data = cfg["write"]["data"]
                parser = cfg["write"]["parser"]
                dynamic = cfg["write"]["dynamic"]

                frame = ModbusFrame(self._device_id, self._func_codes["read"], addr)
                if data:
                    frame.append((data, 2))

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
            print(cmd_bytes)

        raw = self._read_register(cmd_bytes, self.averages if parser else 1)
        return parser(raw) if parser else raw

    def _write_register(self, cmd_bytes):
        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            ser.write(cmd_bytes)
            response_data = ser.read(self._max_data_len)
        return response_data

    def write(self, command, raw_val=None):
        cmd_bytes_template, encoder, dynamic = self._write_commands[command]

        if encoder:
            data = encoder(raw_val)
        else:
            data = raw_val
        data = (data, self._register_byte_width)

        cmd_bytes = ModbusFrame(cmd_bytes_template, data).build() if dynamic else cmd_bytes_template
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
