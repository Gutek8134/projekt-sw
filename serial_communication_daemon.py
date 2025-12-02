import serial
from multiprocessing import Queue
from multiprocessing.synchronize import Event


def serial_daemon(message_queue: "Queue[str]", playlist_update_event: Event) -> None:
    # serial_connection = serial.Serial(port="/dev/ttyS0", baudrate=9600)
    # serial_connection.open()

    # while serial_connection.is_open:
    #     message = serial_connection.readline()

    print("Serial connection closed")
