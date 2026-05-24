from config import DEVICE_ID, PORT, BAUD, TIMEOUT_SEC, AVERAGES
from jyme02 import JYME02
from config import READ_REQUESTS, WRITE_REQUESTS

if __name__ == "__main__":
    encoder = JYME02(DEVICE_ID, PORT, BAUD, TIMEOUT_SEC, AVERAGES)
    encoder.write_angle(100)

    test_result = []

    for _ in range(10):
        test_result.append(encoder.read_angle())

    print("Passed" if all(i == 100 for i in test_result) else "Failed")
    print(test_result)
