from config import DEVICE_ID, PORT, BAUD, TIMEOUT_SEC
from jyme02 import JYME02

if __name__ == "__main__":
    JYME02(DEVICE_ID, PORT, BAUD, TIMEOUT_SEC).benchmark_read()
