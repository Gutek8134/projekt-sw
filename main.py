from adb_shell.adb_device import AdbDeviceUsb
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from pathlib import Path
import os
import multiprocessing
from music_daemon import music_player_daemon
from serial_communication_daemon import serial_daemon
from web_server import web_server
from datetime import time, datetime
from multiprocessing.managers import DictProxy, ValueProxy
from queue import Queue
from ctypes import c_wchar_p
from time import sleep
import json

PLAYLISTS_FILE = "playlists.json"
RFIDS_FILE = "rfids.json"


def save(playlists_dict: dict[str, list[tuple[time, str, str]]], rfids_dict: dict[str, str]):
    with open(PLAYLISTS_FILE, "w") as f:
        json.dump({k: [(v[0].hour, v[0].minute, v[1], v[2])
                  for v in l] for k, l in playlists_dict.items()}, f)

    with open(RFIDS_FILE, "w") as f:
        json.dump(rfids_dict, f)


def connect_to_adb_device() -> AdbDeviceUsb:
    private_key = Path(os.environ.get(
        "KEY_PATH", "~/.android_key/key").replace("~/", str(Path.home())+"/", 1))
    public_key = Path(str(private_key)+".pub")
    if not private_key.exists() or not public_key.exists():
        keygen(str(private_key))
    signer = PythonRSASigner(public_key.read_bytes(), private_key.read_bytes())

    device: AdbDeviceUsb = AdbDeviceUsb()
    device.connect(rsa_keys=[signer])
    return device


def main() -> None:
    device: "AdbDeviceUsb | None" = connect_to_adb_device() if os.name == "posix" else None

    with multiprocessing.Manager() as manager:
        playlist_update_event = manager.Event()

        with open(PLAYLISTS_FILE, "r") as f:
            deserialized: dict[str,
                               list[tuple[int, int, str, str]]] = json.load(f)
            shared_playlists: "DictProxy[str, list[tuple[time, str, str]]]" = manager.dict(
                {k: [(time(v[0], v[1]), v[2], v[3]) for v in l] for k, l in deserialized.items()})

        with open(PLAYLISTS_FILE, "r") as f:
            user_rfids: "DictProxy[str, str]" = manager.dict(json.load(f))
        last_read_rfid: "ValueProxy[str]" = manager.Value(c_wchar_p, "")
        queue: "Queue[str]" = manager.Queue()
        user: "ValueProxy[str]" = manager.Value(c_wchar_p, "default_user")

        # now = datetime.now()
        # shared_playlists["default_user"] = [
        #     (time(now.hour, now.minute+1, now.second), "Holographic Universe", "Fear Catalyst")]
        # print(shared_playlists)

        music_demon_process = multiprocessing.Process(
            target=music_player_daemon, args=(device, shared_playlists, user_rfids, queue, user, playlist_update_event), daemon=False)
        serial_communication_process = multiprocessing.Process(
            target=serial_daemon, args=(queue, last_read_rfid), daemon=True)
        web_server_process = multiprocessing.Process(
            target=web_server, args=(user_rfids, queue, playlist_update_event), daemon=True)

        processes = (music_demon_process,
                     #  serial_communication_process,
                     web_server_process)

        for process in processes:
            process.start()

        while (command := input()) != "exit":
            if command == "save":
                save(dict(shared_playlists), dict(user_rfids))
            elif command == "load":
                with open(PLAYLISTS_FILE, "r") as f:
                    shared_playlists.clear()
                    shared_playlists.update(json.load(f))

                with open(RFIDS_FILE, "r") as f:
                    user_rfids.clear()
                    user_rfids.update(json.load(f))

        save(dict(shared_playlists), dict(user_rfids))

    # Cleanup
    music_demon_process.terminate()


if __name__ == "__main__":
    main()
