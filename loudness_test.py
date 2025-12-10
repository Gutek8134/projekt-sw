from adb_shell.adb_device import AdbDeviceUsb
from main import connect_to_adb_device
from music_daemon import play, change_volume, ease, MAX_VOLUME
from math import ceil
from typing import Iterator
from time import sleep
import os


def nrange(n: int) -> Iterator[float]:
    for i in range(n):
        yield (i+1)/n


def main() -> None:
    device: "AdbDeviceUsb | None" = connect_to_adb_device() if os.name == "posix" else None
    play(device, "Holographic Universe", "Fear Catalyst")

    for v in nrange(10):
        print(ease(v)*MAX_VOLUME)
        change_volume(device, v)
        sleep(5)


if __name__ == "__main__":
    main()
