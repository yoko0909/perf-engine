from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, SessionPhase, SessionState
from perfengine.ui.bridge import BridgeApi


class FakeService:
    def list_devices(self):
        return [DeviceInfo(device_id="SERIAL1", display_name="Pixel 8", connection_type="usb")]

    def list_apps(self, device_id: str):
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]

    def start_session(self, device_id: str, package_name: str):
        return SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="采集中",
        )

    def stop_session(self):
        return SessionState(
            phase=SessionPhase.STOPPED,
            selectors_locked=False,
            message="已停止",
        )

    def get_live_snapshot(self):
        from perfengine.app.models import LiveSnapshot

        return LiveSnapshot(
            session=self.start_session("SERIAL1", "com.demo.app"),
            status=PhoneStatus(
                connection_state="connected",
                device_label="Pixel 8",
                screen_state="on",
                app_state="running",
                battery_level=80,
                temperature_c=31.5,
                last_updated_at="2026-04-24T00:00:00Z",
            ),
            metrics=[],
        )


def test_bridge_api_returns_json_ready_payload():
    bridge = BridgeApi(FakeService())

    devices = bridge.list_devices()
    state = bridge.start_session("SERIAL1", "com.demo.app")
    snapshot = bridge.get_live_snapshot()

    assert devices[0]["device_id"] == "SERIAL1"
    assert state["phase"] == "running"
    assert snapshot["status"]["app_state"] == "running"
