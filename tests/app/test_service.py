from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, SessionPhase
from perfengine.app.service import PerfToolService


class FakeDeviceProvider:
    def list_devices(self):
        return [DeviceInfo(device_id="SERIAL1", display_name="Pixel 8", connection_type="usb")]


class FakeAppProvider:
    def list_apps(self, device_id: str):
        assert device_id == "SERIAL1"
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]


class FakeCollector:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.started = False

    def begin(self, device_id: str, package_name: str):
        if self.should_fail:
            raise RuntimeError("collector failed")
        self.started = True

    def stop(self):
        self.started = False

    def read(self, device_id: str, package_name: str):
        return (
            PhoneStatus(
                connection_state="connected",
                device_label=device_id,
                screen_state="on",
                app_state="running",
                battery_level=88,
                temperature_c=33.5,
                last_updated_at="2026-04-24T00:00:00Z",
            ),
            None,
        )


def test_start_session_locks_selectors():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=FakeCollector(),
    )

    service.list_devices()
    service.list_apps("SERIAL1")
    state = service.start_session("SERIAL1", "com.demo.app")

    assert state.phase is SessionPhase.RUNNING
    assert state.selectors_locked is True


def test_start_session_failure_returns_error_state():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=FakeCollector(should_fail=True),
    )

    state = service.start_session("SERIAL1", "com.demo.app")

    assert state.phase is SessionPhase.ERROR
    assert state.selectors_locked is False
    assert state.message == "Collection could not be started."


def test_stop_session_restores_setup_controls():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=FakeCollector(),
    )

    service.start_session("SERIAL1", "com.demo.app")
    state = service.stop_session()

    assert state.phase is SessionPhase.STOPPED
    assert state.selectors_locked is False
    assert state.message == "Collection stopped."
