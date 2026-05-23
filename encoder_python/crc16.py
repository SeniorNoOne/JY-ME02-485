def generate_crc16_table():
    table = []

    for i in range(256):
        crc = i

        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

        table.append(crc & 0xFFFF)

    return table


def calc_crc16_naive(data, little_endian=True):
    crc = 0xFFFF

    for byte in data:
        crc ^= byte

        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    crc &= 0xFFFF

    return int.to_bytes(crc, 2, byteorder='little' if little_endian else 'big')


def calc_crc16(data, little_endian=True):
    crc = 0xFFFF

    for byte in data:
        crc = (crc >> 8) ^ CRC16_TABLE[(crc ^ byte) & 0xFF]

    crc &= 0xFFFF

    return int.to_bytes(crc, 2, byteorder='little' if little_endian else 'big')


def append_crc16(data, little_endian=True, crc_func=calc_crc16_naive):
    crc = crc_func(data, little_endian=little_endian)
    return data + crc


CRC16_TABLE = generate_crc16_table()
