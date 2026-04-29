from perfengine.android.adb_client import AdbClient
from perfengine.android.app_provider import AppProvider
from perfengine.android.device_provider import DeviceProvider
from perfengine.android.status_provider import StatusProvider


class FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ""


def fake_runner_factory(outputs):
    def _runner(cmd):
        key = " ".join(cmd)
        return FakeCompletedProcess(stdout=outputs.get(key, ""), returncode=0 if key in outputs else 1)

    return _runner


def test_device_provider_parses_adb_devices_output():
    outputs = {
        "adb devices -l": (
            "List of devices attached\n"
            "SERIAL1 device product:husky model:Pixel_8 device:husky transport_id:1\n"
        )
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = DeviceProvider(client)

    devices = provider.list_devices()

    assert devices[0].device_id == "SERIAL1"
    assert devices[0].display_name == "Pixel_8"


def test_status_provider_uses_unknown_when_screen_state_is_missing():
    outputs = {
        "adb -s SERIAL1 shell dumpsys battery": "level: 87\ntemperature: 320\n",
        "adb -s SERIAL1 shell dumpsys power": "Display Power: state=\n",
        "adb -s SERIAL1 shell pidof com.demo.app": "2314\n",
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = StatusProvider(client)

    status = provider.get_phone_status("SERIAL1", "com.demo.app")

    assert status.battery_level == 87
    assert status.temperature_c == 32.0
    assert status.screen_state == "unknown"
    assert status.app_state == "running"


def test_app_provider_returns_package_names_as_labels():
    outputs = {
        "adb -s SERIAL1 shell pm list packages -3": (
            "package:com.demo.app\n"
            "package:com.android.settings\n"
        )
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = AppProvider(client)

    apps = provider.list_apps("SERIAL1")

    assert apps[0].package_name == "com.android.settings"
    assert apps[0].display_name == "com.android.settings"
    assert apps[1].package_name == "com.demo.app"
