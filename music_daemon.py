from adb_shell.adb_device import AdbDeviceUsb
import os
import subprocess
import pause
from datetime import datetime

MUSIC_DIRECTORY_PATH = "/storage/6263-3431/Videoloader"


def sleep_until(hour: int, minute: int = 0, day: datetime = datetime.today()) -> None:
    future = datetime(day.year, day.month, day.day, hour, minute)
    pause.until(future)


def play(device: "AdbDeviceUsb | None", album: str, song: str) -> None:
    if os.name == "posix":
        assert device is not None, "Music daemon: PLAY: device set to None"
        response = device.shell(
            f"am start -a android.intent.action.VIEW -d \"file://{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3\" -t audio/mp3", decode=True)
    else:
        subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW",
                        "-d", f"file://{MUSIC_DIRECTORY_PATH}/{song}.mp3", "-t", "audio/mp3"])


def music_player_daemon(device: "AdbDeviceUsb | None") -> None:
    pass
