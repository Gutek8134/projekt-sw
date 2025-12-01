import serial


def serial_daemon() -> None:
    serial_connection = serial.Serial(port="/dev/ttyS0", baudrate=9600)
    serial_connection.open()
