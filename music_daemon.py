from adb_shell.adb_device import AdbDeviceUsb
import os
from os.path import abspath
import subprocess
import multiprocessing
from multiprocessing.synchronize import Event
from multiprocessing.managers import DictProxy, ListProxy, SyncManager, ValueProxy
from itertools import cycle
from datetime import datetime, time, timedelta

MUSIC_DIRECTORY_PATH = "/storage/sdcard0/Videoloader"
LOCAL_MUSIC_PATH = "./music"


def next_datetime(now: datetime, time: time) -> datetime:
    future = now.replace(hour=time.hour, minute=time.minute)
    while future <= now+timedelta(seconds=30):
        future += timedelta(days=1)
    return future


def scheduled_player(device: "AdbDeviceUsb | None", playlists: "DictProxy[str, list[tuple[time, str, str]]]", current_user: "ValueProxy[str]", playlist_update_event: Event) -> None:
    current_playlist: list[tuple[time, str, str]
                           ] = playlists[current_user.get()]
    # Sort by time
    current_playlist.sort(key=lambda t: next_datetime(datetime.now(), t[0]))

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
        current_playlist: list[tuple[time, str, str]
                               ] = playlists[current_user.get()]
        current_playlist.sort(
            key=lambda t: next_datetime(datetime.now(), t[0]))

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

        response = device.shell(
            f"am start -a android.intent.action.VIEW -d \"file://{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3\" -t audio/mp3", decode=True)
        # print(response)
    else:
        subprocess.run(["adb", "shell", "am", "start", "-a", "android.intent.action.VIEW",
                        "-d", f"file://{MUSIC_DIRECTORY_PATH}/{song}.mp3", "-t", "audio/mp3"])


def music_player_daemon(device: "AdbDeviceUsb | None", shared_playlists: "DictProxy[str, list[tuple[time, str, str]]]", message_queue: "multiprocessing.Queue[str]", current_user: "ValueProxy[str]", playlist_update_event: Event) -> None:
    multiprocessing.Process(target=scheduled_player,
                            args=(device, shared_playlists, current_user, playlist_update_event), daemon=True).start()

    while True:
        message = message_queue.get()

        if message == "STOP":
            break

        else:
            print(message)
