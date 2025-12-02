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
        shared_playlists: "DictProxy[str, list[tuple[time, str, str]]]" = manager.dict(
        )
        queue: "Queue[str]" = manager.Queue()
        user: "ValueProxy[str]" = manager.Value(c_wchar_p, "default_user")

        now = datetime.now()
        shared_playlists["default_user"] = [
            (time(now.hour, now.minute+1, now.second), "Holographic Universe", "Fear Catalyst")]
        print(shared_playlists)

        music_demon_process = multiprocessing.Process(
            target=music_player_daemon, args=(device, shared_playlists, queue, user, playlist_update_event), daemon=False)
        serial_communication_process = multiprocessing.Process(
            target=serial_daemon, args=(queue, playlist_update_event), daemon=True)
        web_server_process = multiprocessing.Process(
            target=web_server, args=(queue, playlist_update_event), daemon=True)

        processes = (music_demon_process,
                     serial_communication_process, web_server_process)

        for process in processes:
            process.start()

        while input() != "exit":
            pass

    # Cleanup
    music_demon_process.terminate()


if __name__ == "__main__":
    main()
