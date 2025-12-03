import serial
from multiprocessing import Queue
from multiprocessing.managers import ValueProxy

MIN_DISTANCE = 6
MAX_DISTANCE = 50


def avg(iterable):
    return sum(iterable)/len(iterable)


def serial_daemon(message_queue: "Queue[str]", last_read_rfid: "ValueProxy[str]") -> None:
    serial_connection = serial.Serial(port="/dev/ttyS0", baudrate=9600)
    serial_connection.reset_input_buffer()
    if not serial_connection.is_open:
        serial_connection.open()

    distances: list[float] = []

    while serial_connection.is_open:
        message = serial_connection.readline().decode()

        if message.startswith("Distance:"):
            distance = float(message.removeprefix("Distance:").strip())
            distances.append(distance)
            if len(distances) == 5:
                average = avg(distances)
                volume: float
                if average < MIN_DISTANCE:
                    volume = 0.
                elif average > MAX_DISTANCE:
                    volume = 1.
                else:
                    volume = (average-MIN_DISTANCE)/(MAX_DISTANCE-MIN_DISTANCE)

                message_queue.put(f"change volume {volume:.2f}")
                distances.clear()
            continue

        if message.startswith("USER ID tag :"):
            message = message.removeprefix("USER ID tag :")
            print("".join(message.split()))
            last_read_rfid.set("".join(message.split()))
            message = "change user RFID " + message
            message_queue.put(message)

    print("Serial connection closed")


# if __name__ == "__main__":
#     serial_connection = serial.Serial(port="/dev/ttyS0", baudrate=9600)
#     serial_connection.reset_input_buffer()
#     if not serial_connection.is_open:
#         serial_connection.open()

#     distances: list[float] = []

#     while serial_connection.is_open:
#         message = serial_connection.readline().decode()

#         if message.startswith("Distance:"):
#             distance = float(message.removeprefix("Distance:").strip())
#             distances.append(distance)
#             if len(distances) == 5:
#                 average = avg(distances)
#                 volume: float
#                 if average < MIN_DISTANCE:
#                     volume = 0.
#                 elif average > MAX_DISTANCE:
#                     volume = 1.
#                 else:
#                     volume = (average-MIN_DISTANCE)/(MAX_DISTANCE-MIN_DISTANCE)

#                 print(f"change volume {volume:.2f}")
#                 distances.clear()
#             continue

#         if message.startswith("USER ID tag :"):
#             message = message.removeprefix("USER ID tag :")
#             print("".join(message.split()))
#             message = "change user RFID " + message
#             print(message.split())

#     print("Serial connection closed")
