import serial

from config import MAX_DATA_LEN, READ_REQUESTS, WRITE_REQUESTS, REGISTER_BYTE_WIDTH
from modbus import ModbusFrame


class JYME02:
    def __init__(self, device_id, com, baud=9600, timeout=0.02, averages=5):
        self.com = com
        self.baud = baud
        self.timeout = timeout
        self.device_id = device_id
        self.averages = averages

        self._read_commands = READ_REQUESTS
        self._write_commands = WRITE_REQUESTS

    def _read_register(self, cmd_bytes, averages):
        accum = 0

        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            for _ in range(averages):
                ser.write(cmd_bytes)
                response_data = ser.read(MAX_DATA_LEN)
                accum += int.from_bytes(response_data[3:5], "big")

        return accum / averages

    def read(self, command):
        cmd_bytes, parser = self._read_commands[command]
        raw = self._read_register(cmd_bytes, self.averages if parser else 1)
        return parser(raw) if parser else raw

    def _write_register(self, cmd_bytes):
        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            ser.write(cmd_bytes)
            response_data = ser.read(MAX_DATA_LEN)
        return response_data

    def write(self, command, raw_val=None):
        cmd_bytes_template, encoder, dynamic = self._write_commands[command]

        if encoder:
            data = encoder(raw_val)
        else:
            data = raw_val
        data = (data, REGISTER_BYTE_WIDTH)

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
