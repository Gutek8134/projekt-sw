from adb_shell.adb_device import AdbDeviceUsb
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from pathlib import Path
from os import environ
from sys import argv

MUSIC_DIRECTORY_PATH = "/storage/6263-3431/Videoloader"


def play(device: AdbDeviceUsb, album: str, song: str):
    response = device.shell(
        f"am start -a android.intent.action.VIEW -d \"file://{MUSIC_DIRECTORY_PATH}/{album}/{song}.mp3\" -t audio/mp3", decode=True)
    print(response)


def main() -> None:
    private_key = Path(environ.get(
        "KEY_PATH", "~/.android_key/key").replace("~/", str(Path.home())+"/", 1))
    public_key = Path(str(private_key)+".pub")
    if not private_key.exists() or not public_key.exists():
        keygen(str(private_key))

    signer = PythonRSASigner(public_key.read_bytes(), private_key.read_bytes())

    device: AdbDeviceUsb = AdbDeviceUsb()
    device.connect(rsa_keys=[signer])

    play(device, argv[1], argv[2])


if __name__ == "__main__":
    main()
