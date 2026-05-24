from config import DEVICE_ID, PORT, BAUD, TIMEOUT_SEC
from jyme02 import JYME02
from config import READ_REQUESTS, WRITE_REQUESTS

if __name__ == "__main__":
    # JYME02(DEVICE_ID, PORT, BAUD, TIMEOUT_SEC).benchmark_read()
    for i, j in WRITE_REQUESTS.items():
        print(i, j)
    print(JYME02(DEVICE_ID, PORT, BAUD, TIMEOUT_SEC).write_angle(0))
    print(JYME02(DEVICE_ID, PORT, BAUD, TIMEOUT_SEC).read_angle())
