from pathlib import Path

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.client import IOSClient
from perfengine.ios.pymobiledevice import IOSProcessStatus
from perfengine.ios.pymobiledevice import IOSBatterySnapshot, IOSSystemSnapshot
from perfengine.ios.tooling import IOSTooling
from perfengine.ios.tunnel import IOSTunnelManager


class FakeDeviceAdapter:
    def __init__(self):
        self.connected = []
        self.prepared_services = 0
        self.started_collectors = []
        self.stopped_collectors = 0
        self.status = IOSProcessStatus(pid=123, running=True, name="Example")
        self.system_snapshot = IOSSystemSnapshot(app_cpu_percent=12.5, total_cpu_percent=42.0, phys_footprint=104857600, memory_mb=100.0)
        self.battery_snapshot = IOSBatterySnapshot(battery_level=88, temperature_c=22.75)
        self.fps_sample = {"fps": 59.7}
        self.app_lists = {}
        self.list_app_calls = []
        self.tunnel_info_urls = []

    def connect(self, device_id: str, *, tunnel_info_url: str | None = None):
        self.connected.append(device_id)
        self.tunnel_info_urls.append(tunnel_info_url)

    def prepare_developer_services(self):
        self.prepared_services += 1

    def get_process_status(self, package_name: str):
        if isinstance(self.status, Exception):
            raise self.status
        return self.status

    def start_collectors(self, pid: int):
        self.started_collectors.append(pid)

    def stop_collectors(self):
        self.stopped_collectors += 1

    def read_system_sample(self):
        return self.system_snapshot

    def read_fps_sample(self):
        return self.fps_sample

    def read_battery_sample(self):
        return self.battery_snapshot

    def list_apps(self, device_id: str):
        self.list_app_calls.append(device_id)
        return self.app_lists.get(device_id, [])


def create_tooling(tmp_path: Path) -> IOSTooling:
    assets_dir = tmp_path / "assets" / "ios"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "ios.exe").write_text("", encoding="utf-8")
    (assets_dir / "sib.exe").write_text("", encoding="utf-8")
    return IOSTooling(root_dir=tmp_path)


def test_client_uses_pymobiledevice_adapter_for_app_list(tmp_path: Path):
    adapter = FakeDeviceAdapter()
    adapter.app_lists["UDID1"] = [
        {"CFBundleIdentifier": "com.example.app", "CFBundleDisplayName": "Example"}
    ]
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        runner=lambda cmd: pytest.fail("App list should use pymobiledevice adapter, not sib"),
        device_adapter=adapter,
    )

    apps = client.list_apps("UDID1")

    assert adapter.list_app_calls == ["UDID1"]
    assert apps[0]["CFBundleIdentifier"] == "com.example.app"


def test_client_returns_adapter_app_list_array_output(tmp_path: Path):
    adapter = FakeDeviceAdapter()
    adapter.app_lists["UDID1"] = [
        {"bundleId": "com.example.alpha", "name": "Alpha"},
        {"bundleId": "com.example.beta", "name": "Beta"},
    ]
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        device_adapter=adapter,
    )

    apps = client.list_apps("UDID1")

    assert apps == [
        {"bundleId": "com.example.alpha", "name": "Alpha"},
        {"bundleId": "com.example.beta", "name": "Beta"},
    ]


def test_client_returns_adapter_app_list_with_non_ascii_names(tmp_path: Path):
    adapter = FakeDeviceAdapter()
    adapter.app_lists["UDID1"] = [
        {"shortVersion": "1.4.11", "version": "26050701", "name": "二重螺旋", "bundleId": "com.hero.dna.ios"},
        {"shortVersion": "7.43.17", "version": "446938450", "name": "飞书", "bundleId": "com.bytedance.ee.lark"},
    ]
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        device_adapter=adapter,
    )

    apps = client.list_apps("UDID1")

    assert apps[0]["name"] == "二重螺旋"
    assert apps[1]["bundleId"] == "com.bytedance.ee.lark"


def test_client_treats_missing_stdout_as_empty_app_list(tmp_path: Path):
    adapter = FakeDeviceAdapter()
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        device_adapter=adapter,
    )

    assert client.list_apps("UDID1") == []


def test_client_prepare_starts_tunnel_manager():
    calls = []
    adapter = FakeDeviceAdapter()

    class FakeTunnel:
        tunnel_info_url = "http://127.0.0.1:5555"

        @staticmethod
        def requires_tunnel(os_version: str | None):
            return True

        def ensure_ready(self, device_id: str, *, os_version: str | None = None):
            calls.append((device_id, os_version))

    client = IOSClient(
        tooling=IOSTooling(root_dir=Path(".")),
        tunnel_manager=FakeTunnel(),
        runner=lambda cmd: None,
        device_adapter=adapter,
    )

    client.prepare("UDID1")

    assert calls == [("UDID1", None)]
    assert adapter.connected == ["UDID1"]
    assert adapter.tunnel_info_urls == ["http://127.0.0.1:5555"]
    assert adapter.prepared_services == 1


def test_client_prepare_skips_tunnel_endpoint_for_ios_versions_before_17():
    calls = []
    adapter = FakeDeviceAdapter()

    class FakeTunnel:
        tunnel_info_url = "http://127.0.0.1:5555"

        @staticmethod
        def requires_tunnel(os_version: str | None):
            return False

        def ensure_ready(self, device_id: str, *, os_version: str | None = None):
            calls.append((device_id, os_version))

    client = IOSClient(
        tooling=IOSTooling(root_dir=Path(".")),
        tunnel_manager=FakeTunnel(),
        device_adapter=adapter,
    )

    client.prepare("UDID1", os_version="15.0")

    assert calls == [("UDID1", "15.0")]
    assert adapter.tunnel_info_urls == [None]


def test_client_get_phone_status_reports_running_process():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    status = client.get_phone_status("UDID1", "com.example.app")

    assert status.connection_state == "connected"
    assert status.device_label == "UDID1"
    assert status.app_state == "running"


def test_client_get_phone_status_reports_missing_process_before_start():
    adapter = FakeDeviceAdapter()
    adapter.status = IOSProcessStatus(pid=None, running=False)
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    status = client.get_phone_status("UDID1", "com.example.app")

    assert status.connection_state == "connected"
    assert status.app_state == "not_running"


def test_client_start_collectors_requires_running_app():
    adapter = FakeDeviceAdapter()
    adapter.status = IOSProcessStatus(pid=None, running=False)
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    with pytest.raises(OperatorError) as exc_info:
        client.start_collectors("UDID1", "com.example.app")

    assert exc_info.value.code == "ios_app_not_running"


def test_client_start_collectors_passes_pid_to_adapter():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    client.start_collectors("UDID1", "com.example.app")

    assert adapter.started_collectors == [123]


def test_client_get_phone_status_reports_exit_after_start():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)
    client.start_collectors("UDID1", "com.example.app")
    adapter.status = IOSProcessStatus(pid=None, running=False)

    status = client.get_phone_status("UDID1", "com.example.app")

    assert status.connection_state == "connected"
    assert status.app_state == "exited"


def test_client_get_phone_status_reports_adapter_disconnect():
    adapter = FakeDeviceAdapter()
    adapter.status = OperatorError(
        code="ios_device_disconnected",
        message="iPhone is not connected. Reconnect it and try again.",
    )
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    status = client.get_phone_status("UDID1", "com.example.app")

    assert status.connection_state == "disconnected"
    assert status.app_state == "unknown"


def test_client_stop_collectors_closes_adapter_collectors():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    client.start_collectors("UDID1", "com.example.app")
    client.stop_collectors("UDID1", "com.example.app")

    assert adapter.stopped_collectors == 1


def test_client_read_system_sample_maps_adapter_snapshot_fields():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    sample = client.read_system_sample("UDID1", "com.example.app")

    assert sample == {
        "app_cpu_percent": 12.5,
        "total_cpu_percent": 42.0,
        "physFootprint": 104857600,
        "memory_mb": 100.0,
    }


def test_client_read_fps_sample_delegates_to_adapter():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    sample = client.read_fps_sample("UDID1", "com.example.app")

    assert sample == {"fps": 59.7}


def test_client_read_battery_sample_maps_adapter_snapshot_fields():
    adapter = FakeDeviceAdapter()
    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), device_adapter=adapter, runner=lambda cmd: None)

    sample = client.read_battery_sample("UDID1")

    assert sample == {
        "battery_level": 88,
        "temperature_c": 22.75,
    }
