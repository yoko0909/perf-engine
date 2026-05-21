from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, SessionPhase
from perfengine.app.service import PerfToolService


class FakeDeviceProvider:
    def __init__(self, devices):
        self._devices = devices

    def list_devices(self):
        return self._devices


class FakeAppProvider:
    def list_apps(self, device_id: str):
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]


class FakeCollector:
    def __init__(self, mode: str):
        self.mode = mode

    def begin(self, device_id: str, package_name: str):
        return None

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        if self.mode == "disconnected":
            return (
                PhoneStatus(
                    connection_state="disconnected",
                    device_label=device_id,
                    screen_state="unknown",
                    app_state="unknown",
                    battery_level=None,
                    temperature_c=None,
                    last_updated_at="2026-04-24T00:00:00Z",
                ),
                None,
            )
        if self.mode == "no-data":
            return (
                PhoneStatus(
                    connection_state="connected",
                    device_label=device_id,
                    screen_state="on",
                    app_state="running",
                    battery_level=80,
                    temperature_c=32.0,
                    last_updated_at="2026-04-24T00:00:00Z",
                ),
                None,
            )
        return (
            PhoneStatus(
                connection_state="connected",
                device_label=device_id,
                screen_state="on",
                app_state="exited",
                battery_level=80,
                temperature_c=32.0,
                last_updated_at="2026-04-24T00:00:00Z",
            ),
            None,
        )


def test_no_device_returns_operator_message():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("no-data"),
    )

    devices = service.list_devices()

    assert devices == []
    assert service.state.message == "No supported devices were detected."


def test_waiting_for_data_keeps_running_state():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([DeviceInfo(device_id="SERIAL1", display_name="Pixel 8")]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("no-data"),
    )

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.RUNNING
    assert snapshot.session.message == "Waiting for device data."


def test_device_disconnect_interrupts_session():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([DeviceInfo(device_id="SERIAL1", display_name="Pixel 8")]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("disconnected"),
    )

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.INTERRUPTED
    assert snapshot.session.message == "Device disconnected during collection."


def test_app_exit_interrupts_session():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([DeviceInfo(device_id="SERIAL1", display_name="Pixel 8")]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("app-exited"),
    )

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.INTERRUPTED
    assert snapshot.session.message == "Target application exited during collection."
