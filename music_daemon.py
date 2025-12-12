from adb_shell.adb_device import AdbDeviceUsb
import os
from os.path import abspath
import subprocess
import multiprocessing
from multiprocessing.synchronize import Event
from multiprocessing.managers import DictProxy, ListProxy, SyncManager, ValueProxy
from itertools import cycle
from datetime import datetime, time, timedelta
from math import sqrt, sin, pi

MUSIC_DIRECTORY_PATH = "/storage/sdcard0/Videoloader"
LOCAL_MUSIC_PATH = "./music"
MAX_VOLUME = 5


def next_datetime(now: datetime, time: time) -> datetime:
    future = now.replace(hour=time.hour, minute=time.minute)
    while future <= now+timedelta(seconds=30):
        future += timedelta(days=1)
    return future


def get_sorting_value(t: tuple[time, str, str]):
    return next_datetime(datetime.now(), t[0])


def scheduled_player(device: "AdbDeviceUsb | None", playlists: "DictProxy[str, ListProxy[tuple[time, str, str]]]", current_user: "ValueProxy[str]", playlist_update_event: Event) -> None:
    current_playlist: ListProxy[tuple[time, str, str]
                                ] = playlists[current_user.get()]
    # Sort by time
    current_playlist.sort(key=get_sorting_value)

    playlist: cycle[tuple[time, str, str]] = cycle(current_playlist)

    while True:
        next_time, next_album, next_song = next(playlist)
        now = datetime.now()
        next_song_datetime = next_datetime(now, next_time)
        print(
            f"Next playing: {next_song} from {next_album} at {next_song_datetime}")

        # timeout in seconds
        # False - ended due to timeout
        while not playlist_update_event.wait((next_song_datetime-now).total_seconds()):
            play(device, next_album, next_song)
            next_time, next_album, next_song = next(playlist)
            now = datetime.now()
            next_song_datetime = next_datetime(now, next_time)
            print(
                f"Next playing: {next_song} from {next_album} at {next_song_datetime}")

        playlist_update_event.clear()

        # Update playlist
        current_playlist: ListProxy[tuple[time, str, str]
                                    ] = playlists[current_user.get()]
        current_playlist.sort(
            key=get_sorting_value)

        playlist: cycle[tuple[time, str, str]] = cycle(current_playlist)


def play(device: "AdbDeviceUsb | None", album: str, song: str) -> None:
    if os.name == "posix":
        assert device is not None, "Music daemon: PLAY: device set to None"

        message = device.shell(f"ls \"{MUSIC_DIRECTORY_PATH}/{album}\"")
        assert isinstance(message, str)
        # print(message)

        if "No such file or directory" in message:
            message = device.shell(f"mkdir \"{MUSIC_DIRECTORY_PATH}/{album}\"")
            # print(message)

        message = device.shell(
            f"ls \"{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3\"")
        assert isinstance(message, str)
        # print(message)

        if "No such file or directory" in message:
            message = device.push(abspath(f"{LOCAL_MUSIC_PATH}/{album}/{song}.mp3"),
                                  f"{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3")
            # print(message)

        device.shell("am force-stop com.android.music")
        response = device.shell(
            f"am start -a android.intent.action.VIEW -d \"file://{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3\" -t audio/mp3", decode=True)
        # print(response)
    else:
        subprocess.run(
            ["adb", "shell", "am", "force-stop", "com.android.music"])
        subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW",
                        "-d", f"file://{MUSIC_DIRECTORY_PATH}/{song}.mp3", "-t", "audio/mp3"])


# Functions taken from https://easings.net/#

def ease_quad(x: float) -> float:
    return 1 - (1 - x) * (1 - x)


def ease_circ(x: float) -> float:
    return sqrt(1 - (x - 1) ** 2)


def ease_sin(x: float) -> float:
    return sin((x * pi) / 2)


ease = ease_sin


def change_volume(device: "AdbDeviceUsb | None", normal_volume: float):
    if os.name == "posix":
        assert device is not None, "Music daemon: PLAY: device set to None"
        message = device.shell(
            f"cmd media_session volume --set {max(1, round(ease(normal_volume)*MAX_VOLUME))}")
        # print(message)
    else:
        subprocess.run(["adb", "shell", "cmd", "media_session",
                       "volume", "--set", repr(max(1, round(ease(normal_volume)*MAX_VOLUME)))])


def change_user_by_rfid(user_rfids: "DictProxy[str, str]", current_user: "ValueProxy[str]", RFID: str):
    current_user.set(user_rfids[RFID])


def music_player_daemon(device: "AdbDeviceUsb | None", shared_playlists: "DictProxy[str, ListProxy[tuple[time, str, str]]]", user_rfids: "DictProxy[str, str]", message_queue: "multiprocessing.Queue[str]", current_user: "ValueProxy[str]", playlist_update_event: Event) -> None:
    multiprocessing.Process(target=scheduled_player,
                            args=(device, shared_playlists, current_user, playlist_update_event), daemon=True).start()
    change_volume(device, 0.6)
    while True:
        message = message_queue.get()

        if message == "STOP":
            break

        else:
            message_split = message.strip().split()
            command = message_split[0].lower()
            arguments = [m.lower() for m in message_split[1:]]
            if command == "change":
                if arguments[0] == "volume":
                    change_volume(device, float(arguments[1]))
                elif arguments[0] == "user":
                    if arguments[1] == "RFID":
                        rfid = "".join(arguments[2:])
                        if rfid not in user_rfids:
                            continue
                        change_user_by_rfid(
                            user_rfids, current_user, rfid)
                    else:
                        current_user.set(" ".join(arguments[1:]))
                        playlist_update_event.set()

                elif arguments[0] == "ease":
                    global ease
                    if arguments[1] == "quad":
                        ease = ease_quad
                    elif arguments[1] == "circ":
                        ease = ease_circ
                    elif arguments[1] == "sin":
                        ease = ease_sin

                    else:
                        print(
                            f"Invalid easing function \"{arguments[1]}\", must be one of 'quad' 'circ' 'sin'")
