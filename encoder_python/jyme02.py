import serial

from config import MAX_DATA_LEN, READ_REQUESTS


class JYME02:
    def __init__(self, device_id, com, baud=9600, timeout=0.02, averages=10):
        self.com = com
        self.baud = baud
        self.timeout = timeout
        self.device_id = device_id
        self.averages = averages

        self._commands = READ_REQUESTS

    def _read_register(self, cmd_bytes, averages):
        accum = 0

        with serial.Serial(self.com, self.baud, timeout=self.timeout) as ser:
            for _ in range(averages):
                ser.write(cmd_bytes)
                response_data = ser.read(MAX_DATA_LEN)
                accum += int.from_bytes(response_data[3:5], "big")

        return accum / averages

    def _write_register(self, cmd_bytes):
        pass

    def read(self, command):
        cmd_bytes, parser = self._commands[command]
        raw = self._read_register(cmd_bytes, self.averages if parser else 1)
        return parser(raw) if parser else raw

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

    def read_angular_vel_sr(self):
        return self.read("angular_vel_sr")

    def read_all(self):
        return self.read("all")

    def benchmark_read(self):
        for param in self._commands:
            method = getattr(self, f"read_{param}")
            if method:
                print(f"{param}: {method()}")
