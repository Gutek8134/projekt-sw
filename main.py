from adb_shell.adb_device import AdbDeviceUsb
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from pathlib import Path
from os import environ


def main() -> None:
    private_key = Path(environ.get(
        "KEY_PATH", "~/.android_key/key").replace("~/", str(Path.home())+"/", 1))
    public_key = Path(str(private_key)+".pub")
    if not private_key.exists() or not public_key.exists():
        keygen(str(private_key))

    signer = PythonRSASigner(public_key.read_bytes(), private_key.read_bytes())

    device = AdbDeviceUsb()
    device.connect(rsa_keys=[signer])

    device.shell("input keyevent 26")


if __name__ == "__main__":
    main()
