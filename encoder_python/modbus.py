class ModbusFrame:
    def __init__(self, *args, little_endian=True, use_lookup_table=False):
        self.little_endian = little_endian
        self._data = b""

        if use_lookup_table:
            self._crc16_table = self._generate_crc16_table()
            self._calc_crc = self._calc_crc16
        else:
            self._crc16_table = None
            self._calc_crc = self._calc_crc16_naive

        for arg in args:
            self._data += self._to_bytes(arg)

    @staticmethod
    def _to_bytes(arg):
        if isinstance(arg, bytes):
            return arg
        elif isinstance(arg, int):
            return bytes([arg])
        elif isinstance(arg, str):
            return bytes.fromhex(arg)
        elif isinstance(arg, tuple):
            # for multi-byte integer fields (value, length)
            value, length = arg
            return value.to_bytes(length, byteorder='big')
        else:
            raise TypeError(f"Unsupported type: {type(arg)}")

    @staticmethod
    def _generate_crc16_table():
        table = []

        for i in range(256):
            crc = i
            for _ in range(8):
                crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
            table.append(crc & 0xFFFF)

        return table

    def _calc_crc16_naive(self):
        crc = 0xFFFF

        for byte in self._data:
            crc ^= byte

            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1

        crc &= 0xFFFF

        return int.to_bytes(crc, 2, byteorder='little' if self.little_endian else 'big')

    def _calc_crc16(self):
        crc = 0xFFFF

        for byte in self._data:
            crc = (crc >> 8) ^ self._crc16_table[(crc ^ byte) & 0xFF]

        crc &= 0xFFFF

        return int.to_bytes(crc, 2, byteorder='little' if self.little_endian else 'big')

    def append(self, *args):
        for arg in args:
            self._data += self._to_bytes(arg)
        return self

    def build(self):
        return self._data + self._calc_crc()
