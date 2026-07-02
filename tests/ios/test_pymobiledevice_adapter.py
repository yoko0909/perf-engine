import logging
import plistlib
import struct
from dataclasses import dataclass
from io import BytesIO
from types import SimpleNamespace
import importlib

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.pymobiledevice import (
    IOSBatterySnapshot,
    IOSCollectorSnapshot,
    IOSProcessStatus,
    IOSSystemSnapshot,
    PymobiledeviceIOSAdapter,
    _map_pymobiledevice_error,
    summarize_coreprofile_chunk,
)


class FakeAsyncService:
    def __init__(self):
        self.close_calls = 0

    async def close(self):
        self.close_calls += 1


class FailingProcessControl:
    async def process_identifier_for_bundle_identifier(self, package_name: str):
        raise RuntimeError("InvalidService processcontrol")


class SyncProcessControl:
    def __init__(self, pid):
        self.pid = pid
        self.queries = []

    def process_identifier_for_bundle_identifier(self, package_name: str):
        self.queries.append(package_name)
        return self.pid


class FakeDvtSecureSocketProxy:
    def __init__(self, service_provider):
        self.service_provider = service_provider
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exited = True


@dataclass
class FakeProcessAttributes:
    cpuTotalUser: float | None = None
    cpuTotalSystem: float | None = None
    physFootprint: int | None = None
    memResidentSize: int | None = None
    cpuUsage: float | None = None


class FakeSyncSysmontap:
    process_attributes_cls = FakeProcessAttributes

    def __init__(self, dvt, *, rows=None):
        self.dvt = dvt
        self.entered = False
        self.exited = False
        self.rows = iter(rows or [
            {
                "CPUUsage": 42.0,
                "Processes": {123: [1.0, 2.0, 104857600, 52428800]},
            }
        ])

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exited = True

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.rows)


class FakeCreatableSysmontap(FakeSyncSysmontap):
    created_with = []

    @classmethod
    async def create(cls, dvt):
        cls.created_with.append(dvt)
        return cls(dvt)


class FakeAsyncGraphics:
    def __init__(self, dvt, rows):
        self.dvt = dvt
        self.rows = list(rows)
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.rows:
            raise StopAsyncIteration
        return self.rows.pop(0)


class FakeUsbmuxDevice:
    def __init__(self, serial: str, *, connection_type: str = "USB"):
        self.serial = serial
        self.connection_type = connection_type
        self.is_usb = connection_type.lower() == "usb"
        self.is_network = connection_type.lower() == "network"


class FakeLockdown:
    def __init__(self, serial: str, *, short_info=None):
        self.udid = serial
        self.short_info = short_info or {
            "DeviceName": f"{serial} Phone",
            "ProductType": "iPhone14,5",
            "ProductVersion": "18.3",
        }


class FakeInstallationProxy:
    def __init__(self, apps):
        self.apps = apps
        self.connected = False
        self.closed = False

    async def connect(self):
        self.connected = True

    async def get_apps(self, application_type="User"):
        return self.apps

    async def close(self):
        self.closed = True


class FakeRemoteServiceDiscovery:
    def __init__(self, address):
        self.address = address
        self.connected = False

    async def connect(self):
        self.connected = True

    async def close(self):
        self.connected = False


class FlakyRemoteServiceDiscovery:
    def __init__(self, address, *, failures_before_success: int):
        self.address = address
        self.failures_before_success = failures_before_success
        self.connect_calls = 0
        self.connected = False

    async def connect(self):
        self.connect_calls += 1
        if self.connect_calls <= self.failures_before_success:
            raise OSError("[WinError 1231] network location cannot be reached")
        self.connected = True

    async def close(self):
        self.connected = False


async def async_value():
    return "ready"


async def async_failure():
    raise RuntimeError("library exploded")


async def async_pairing_failure():
    raise RuntimeError("InvalidHostID pairing failure from pymobiledevice3")


async def async_dvt_failure():
    raise RuntimeError("com.apple.instruments.server.services.sysmontap InvalidService")


def test_snapshot_dataclasses_store_project_owned_fields():
    process = IOSProcessStatus(pid=123, running=True, name="Game")
    system = IOSSystemSnapshot(
        app_cpu_percent=12.5,
        total_cpu_percent=45.0,
        phys_footprint=104857600,
        memory_mb=100.0,
    )
    battery = IOSBatterySnapshot(battery_level=88, temperature_c=22.75)
    collector = IOSCollectorSnapshot(fps={}, system=system, battery=battery)

    assert process.pid == 123
    assert process.running is True
    assert system.phys_footprint == 104857600
    assert collector.battery.temperature_c == 22.75


def test_sync_bridge_returns_async_result():
    adapter = PymobiledeviceIOSAdapter()

    assert adapter._run_async(async_value()) == "ready"


def test_sync_bridge_maps_async_failure_to_operator_error():
    adapter = PymobiledeviceIOSAdapter()

    with pytest.raises(OperatorError) as exc_info:
        adapter._run_async(async_failure())

    assert exc_info.value.code == "ios_pymobiledevice_error"
    assert "library exploded" not in exc_info.value.message


def test_error_mapping_logs_diagnostic_phase_without_exposing_ui_message(caplog):
    with caplog.at_level(logging.ERROR, logger="perfengine.ios.pymobiledevice"):
        error = _map_pymobiledevice_error(RuntimeError("opaque library failure"), phase="query process status")

    assert error.code == "ios_pymobiledevice_error"
    assert "opaque library failure" not in error.message
    assert "query process status" in caplog.text
    assert "RuntimeError" in caplog.text


def test_sync_bridge_maps_pairing_failure_to_operator_error_without_raw_text():
    adapter = PymobiledeviceIOSAdapter()

    with pytest.raises(OperatorError) as exc_info:
        adapter._run_async(async_pairing_failure())

    assert exc_info.value.code == "ios_pairing_required"
    assert "InvalidHostID" not in exc_info.value.message
    assert "pymobiledevice3" not in exc_info.value.message


def test_sync_bridge_maps_dvt_service_failure_to_operator_error_without_raw_text():
    adapter = PymobiledeviceIOSAdapter()

    with pytest.raises(OperatorError) as exc_info:
        adapter._run_async(async_dvt_failure())

    assert exc_info.value.code == "ios_developer_services_unavailable"
    assert "InvalidService" not in exc_info.value.message
    assert "sysmontap" not in exc_info.value.message


def test_missing_pywin32_maps_to_operator_error_without_raw_text():
    error = _map_pymobiledevice_error(ModuleNotFoundError("No module named 'win32security'"))

    assert error.code == "ios_pymobiledevice_unavailable"
    assert "win32security" not in error.message


def test_unavailable_operator_error_logs_original_import_failure(caplog):
    with caplog.at_level(logging.ERROR, logger="perfengine.ios.pymobiledevice"):
        error = PymobiledeviceIOSAdapter._unavailable_import_error(
            ModuleNotFoundError("No module named 'pymobiledevice3.services.dvt.dvt_secure_socket_proxy'"),
            phase="import dvt secure socket proxy",
        )

    assert error.code == "ios_pymobiledevice_unavailable"
    assert "dvt_secure_socket_proxy" not in error.message
    assert "import dvt secure socket proxy" in caplog.text
    assert "ModuleNotFoundError" in caplog.text


def test_default_dvt_service_falls_back_to_dvt_provider_when_demo_proxy_module_is_missing(monkeypatch):
    class FakeDvtProvider:
        def __init__(self, service_provider):
            self.service_provider = service_provider

    original_import_module = importlib.import_module

    def fake_import_module(name, package=None):
        if name == "pymobiledevice3.services.dvt.dvt_secure_socket_proxy":
            raise ModuleNotFoundError("No module named 'pymobiledevice3.services.dvt.dvt_secure_socket_proxy'")
        if name == "pymobiledevice3.services.dvt.instruments.dvt_provider":
            return SimpleNamespace(DvtProvider=FakeDvtProvider)
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    service = PymobiledeviceIOSAdapter._default_dvt_service("LOCKDOWN")

    assert isinstance(service, FakeDvtProvider)
    assert service.service_provider == "LOCKDOWN"


def test_pid_lookup_failure_maps_to_operator_error_without_raw_text():
    adapter = PymobiledeviceIOSAdapter()
    adapter.process_control = FailingProcessControl()

    with pytest.raises(OperatorError) as exc_info:
        adapter.get_process_status("com.example.app")

    assert exc_info.value.code == "ios_developer_services_unavailable"
    assert "InvalidService" not in exc_info.value.message


def test_process_status_accepts_demo_style_synchronous_process_control():
    process_control = SyncProcessControl(pid=123)
    adapter = PymobiledeviceIOSAdapter()
    adapter.process_control = process_control

    status = adapter.get_process_status("com.example.app")

    assert status == IOSProcessStatus(pid=123, running=True)
    assert process_control.queries == ["com.example.app"]


def test_process_status_creates_demo_style_dvt_secure_socket_proxy():
    dvt_services = []
    process_controls = []

    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    def fake_dvt_service_factory(service_provider):
        service = FakeDvtSecureSocketProxy(service_provider)
        dvt_services.append(service)
        return service

    def fake_process_control_factory(dvt):
        process_control = SyncProcessControl(pid=456)
        process_controls.append((dvt, process_control))
        return process_control

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        dvt_service_factory=fake_dvt_service_factory,
        process_control_factory=fake_process_control_factory,
    )

    adapter.connect("UDID1")
    status = adapter.get_process_status("com.example.app")
    adapter.close()

    assert status == IOSProcessStatus(pid=456, running=True)
    assert dvt_services[0].entered is True
    assert dvt_services[0].exited is True
    assert process_controls[0][0] is dvt_services[0]


def test_connect_uses_async_usbmux_factory():
    calls = []
    fake_lockdown = object()

    async def fake_create_using_usbmux(*, serial):
        calls.append(serial)
        return fake_lockdown

    adapter = PymobiledeviceIOSAdapter(create_using_usbmux=fake_create_using_usbmux)

    adapter.connect("UDID1")

    assert calls == ["UDID1"]
    assert adapter.lockdown is fake_lockdown


def test_list_devices_uses_pymobiledevice_usbmux_and_lockdown_short_info():
    calls = []

    async def fake_list_devices():
        return [FakeUsbmuxDevice("UDID1")]

    async def fake_create_using_usbmux(*, serial):
        calls.append(serial)
        return FakeLockdown(serial)

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        list_usbmux_devices=fake_list_devices,
    )

    devices = adapter.list_devices()

    assert calls == ["UDID1"]
    assert devices == [
        {
            "udid": "UDID1",
            "DeviceName": "UDID1 Phone",
            "ProductType": "iPhone14,5",
            "ProductVersion": "18.3",
            "ConnectionType": "USB",
        }
    ]


def test_list_apps_uses_pymobiledevice_installation_proxy():
    fake_proxy = FakeInstallationProxy(
        {
            "com.example.app": {
                "CFBundleDisplayName": "Example",
                "CFBundleShortVersionString": "1.0",
            }
        }
    )

    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        installation_proxy_factory=lambda lockdown: fake_proxy,
    )

    apps = adapter.list_apps("UDID1")

    assert fake_proxy.connected is True
    assert fake_proxy.closed is True
    assert apps == [
        {
            "CFBundleDisplayName": "Example",
            "CFBundleShortVersionString": "1.0",
            "CFBundleIdentifier": "com.example.app",
        }
    ]


def test_connect_uses_tunnel_endpoint_for_remote_developer_services():
    remote_services = []

    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    def fake_urlopen(url: str, timeout: float):
        assert url == "http://127.0.0.1:5555"
        assert timeout == 1.0
        return BytesIO(b'{"UDID1":{"ip":"fd00::1","port":12345}}')

    def fake_remote_factory(address):
        service = FakeRemoteServiceDiscovery(address)
        remote_services.append(service)
        return service

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        remote_service_discovery_factory=fake_remote_factory,
        tunnel_urlopen=fake_urlopen,
    )

    adapter.connect("UDID1", tunnel_info_url="http://127.0.0.1:5555")

    assert adapter.lockdown.udid == "UDID1"
    assert adapter.developer_provider is remote_services[0]
    assert remote_services[0].address == ("fd00::1", 12345)
    assert remote_services[0].connected is True


def test_connect_retries_remote_developer_service_until_rsd_socket_is_ready():
    remote_services = []

    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    def fake_urlopen(url: str, timeout: float):
        return BytesIO(b'{"UDID1":{"ip":"fd00::1","port":12345}}')

    def fake_remote_factory(address):
        service = FlakyRemoteServiceDiscovery(address, failures_before_success=2)
        remote_services.append(service)
        return service

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        remote_service_discovery_factory=fake_remote_factory,
        tunnel_urlopen=fake_urlopen,
        remote_connect_retry_interval_s=0,
    )

    adapter.connect("UDID1", tunnel_info_url="http://127.0.0.1:5555")

    assert remote_services[0].connect_calls == 3
    assert remote_services[0].connected is True


def test_remote_developer_service_winerror_maps_to_tunnel_unavailable_after_retries():
    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    def fake_urlopen(url: str, timeout: float):
        return BytesIO(b'{"UDID1":{"ip":"fd00::1","port":12345}}')

    def fake_remote_factory(address):
        return FlakyRemoteServiceDiscovery(address, failures_before_success=5)

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        remote_service_discovery_factory=fake_remote_factory,
        tunnel_urlopen=fake_urlopen,
        remote_connect_attempts=2,
        remote_connect_retry_interval_s=0,
    )

    with pytest.raises(OperatorError) as exc_info:
        adapter.connect("UDID1", tunnel_info_url="http://127.0.0.1:5555")

    assert exc_info.value.code == "ios_tunnel_unavailable"


def test_connect_uses_local_userspace_tunnel_port_when_payload_provides_one():
    remote_services = []

    async def fake_create_using_usbmux(*, serial):
        return FakeLockdown(serial)

    def fake_urlopen(url: str, timeout: float):
        return BytesIO(
            b'[{"address":"fd47:1452:e9e9::1","rsdPort":63140,'
            b'"udid":"UDID1","userspaceTun":true,"userspaceTunPort":60109}]'
        )

    def fake_remote_factory(address):
        service = FakeRemoteServiceDiscovery(address)
        remote_services.append(service)
        return service

    adapter = PymobiledeviceIOSAdapter(
        create_using_usbmux=fake_create_using_usbmux,
        remote_service_discovery_factory=fake_remote_factory,
        tunnel_urlopen=fake_urlopen,
    )

    adapter.connect("UDID1", tunnel_info_url="http://127.0.0.1:60105/tunnels")

    assert remote_services[0].address == ("127.0.0.1", 60109)
    assert remote_services[0].connected is True


def test_close_is_idempotent_for_owned_async_services():
    service = FakeAsyncService()
    adapter = PymobiledeviceIOSAdapter()
    adapter._owned_services.append(service)

    adapter.close()
    adapter.close()

    assert service.close_calls == 1
    assert adapter._owned_services == []


def test_system_snapshot_computes_app_cpu_from_cumulative_process_deltas():
    adapter = PymobiledeviceIOSAdapter()
    adapter._active_pid = 123
    process_fields = ["cpuTotalUser", "cpuTotalSystem", "physFootprint", "memResidentSize", "name"]

    adapter._record_sysmontap_sample(
        {
            "CPUUsage": 40.0,
            "Processes": {123: [1.0, 2.0, 104857600, 52428800, "Game"]},
        },
        process_fields=process_fields,
        timestamp=10.0,
    )
    first = adapter.read_system_sample()
    adapter._record_sysmontap_sample(
        {
            "CPUUsage": 42.0,
            "Processes": {123: [1.5, 2.5, 125829120, 62914560, "Game"]},
        },
        process_fields=process_fields,
        timestamp=11.0,
    )

    second = adapter.read_system_sample()

    assert first.app_cpu_percent is None
    assert second.app_cpu_percent == 100.0
    assert second.total_cpu_percent == 42.0
    assert second.phys_footprint == 125829120
    assert second.memory_mb == 120.0


def test_system_snapshot_prefers_demo_sysmontap_cpu_usage_and_total_cpu_shape():
    adapter = PymobiledeviceIOSAdapter()
    adapter._active_pid = 123
    process_fields = ["cpuTotalUser", "cpuTotalSystem", "physFootprint", "memResidentSize", "cpuUsage"]

    adapter._record_sysmontap_sample(
        {
            "CPUCount": 6,
            "SystemCPUUsage": {"CPU_TotalLoad": 180.0},
            "Processes": {123: [1.0, 2.0, 125829120, 52428800, 37.5]},
        },
        process_fields=process_fields,
        timestamp=10.0,
    )

    snapshot = adapter.read_system_sample()

    assert snapshot.app_cpu_percent == 37.5
    assert snapshot.total_cpu_percent == 30.0
    assert snapshot.phys_footprint == 125829120
    assert snapshot.memory_mb == 120.0


def test_system_snapshot_decodes_demo_style_plist_string_rows():
    row = {
        "CPUCount": 4,
        "SystemCPUUsage": {"CPU_TotalLoad": 200.0},
        "Processes": {"123": [1.0, 2.0, 104857600, 52428800, 25.0]},
    }
    row_text = plistlib.dumps(row, fmt=plistlib.FMT_XML).decode("utf-8")
    sysmontap = FakeSyncSysmontap(FakeLockdown("UDID1"), rows=[row_text])

    adapter = PymobiledeviceIOSAdapter(sysmontap_factory=lambda dvt: sysmontap)
    adapter.dvt = FakeDvtSecureSocketProxy(FakeLockdown("UDID1"))

    adapter.start_collectors(123)
    snapshot = adapter.read_system_sample()
    adapter.close()

    assert snapshot.app_cpu_percent == 25.0
    assert snapshot.total_cpu_percent == 50.0
    assert snapshot.memory_mb == 100.0


def test_system_snapshot_keeps_latest_values_when_sysmontap_rows_are_partial_like_demo():
    adapter = PymobiledeviceIOSAdapter()
    adapter._active_pid = 123
    process_fields = ["cpuTotalUser", "cpuTotalSystem", "physFootprint", "memResidentSize", "cpuUsage"]

    adapter._record_sysmontap_sample(
        {
            "CPUCount": 4,
            "SystemCPUUsage": {"CPU_TotalLoad": 120.0},
            "PerCPUUsage": [{"CPU_TotalLoad": 30.0}],
        },
        process_fields=process_fields,
        timestamp=10.0,
    )
    adapter._record_sysmontap_sample(
        {
            "Processes": {123: [1.0, 2.0, 104857600, 52428800, 25.0]},
        },
        process_fields=process_fields,
        timestamp=10.5,
    )

    snapshot = adapter.read_system_sample()

    assert snapshot.total_cpu_percent == 30.0
    assert snapshot.app_cpu_percent == 25.0
    assert snapshot.memory_mb == 100.0


def test_start_collectors_uses_demo_style_synchronous_sysmontap_context():
    dvt_service = FakeDvtSecureSocketProxy(FakeLockdown("UDID1"))
    sysmontaps = []

    def fake_sysmontap_factory(dvt):
        sysmontap = FakeSyncSysmontap(dvt)
        sysmontaps.append(sysmontap)
        return sysmontap

    adapter = PymobiledeviceIOSAdapter(sysmontap_factory=fake_sysmontap_factory)
    adapter.dvt = dvt_service

    adapter.start_collectors(123)
    snapshot = adapter.read_system_sample()
    adapter.close()

    assert sysmontaps[0].entered is True
    assert sysmontaps[0].exited is True
    assert snapshot.total_cpu_percent == 42.0
    assert snapshot.phys_footprint == 104857600


def test_read_fps_sample_uses_graphics_core_animation_fps():
    graphics = FakeAsyncGraphics(
        FakeLockdown("UDID1"),
        rows=[{"CoreAnimationFramesPerSecond": 59.7}],
    )

    adapter = PymobiledeviceIOSAdapter(graphics_factory=lambda dvt: graphics)
    adapter.dvt = FakeDvtSecureSocketProxy(FakeLockdown("UDID1"))

    sample = adapter.read_fps_sample()
    adapter.close()

    assert sample == {"fps": 59.7}
    assert graphics.entered is True
    assert graphics.exited is True


def test_default_sysmontap_uses_creatable_pymobiledevice_service(monkeypatch):
    original_import_module = importlib.import_module
    FakeCreatableSysmontap.created_with = []

    def fake_import_module(name, package=None):
        if name == "pymobiledevice3.services.dvt.instruments.sysmontap":
            return SimpleNamespace(Sysmontap=FakeCreatableSysmontap)
        return original_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    service = PymobiledeviceIOSAdapter()._run_async(
        PymobiledeviceIOSAdapter._default_sysmontap("DVT")
    )

    assert isinstance(service, FakeCreatableSysmontap)
    assert FakeCreatableSysmontap.created_with == ["DVT"]


def test_start_collectors_accepts_async_sysmontap_factory():
    sysmontaps = []

    async def fake_sysmontap_factory(dvt):
        sysmontap = FakeSyncSysmontap(dvt)
        sysmontaps.append(sysmontap)
        return sysmontap

    adapter = PymobiledeviceIOSAdapter(sysmontap_factory=fake_sysmontap_factory)
    adapter.dvt = FakeDvtSecureSocketProxy(FakeLockdown("UDID1"))

    adapter.start_collectors(123)
    snapshot = adapter.read_system_sample()
    adapter.close()

    assert sysmontaps[0].entered is True
    assert sysmontaps[0].exited is True
    assert snapshot.total_cpu_percent == 42.0


def test_battery_snapshot_maps_observed_diagnostics_fields():
    adapter = PymobiledeviceIOSAdapter()

    snapshot = adapter._map_battery_snapshot(
        {
            "CurrentCapacity": 88,
            "Voltage": 4309,
            "InstantAmperage": 2,
            "Temperature": 2959,
        }
    )

    assert snapshot.battery_level == 88
    assert snapshot.temperature_c == 22.75


def test_battery_snapshot_ignores_implausible_temperature():
    adapter = PymobiledeviceIOSAdapter()

    snapshot = adapter._map_battery_snapshot({"CurrentCapacity": 88, "Temperature": 99999})

    assert snapshot.battery_level == 88
    assert snapshot.temperature_c is None


def test_coreprofile_chunk_summary_counts_demo_style_event_codes():
    row_a = struct.pack("<QLLQQQQLLQ", 1, 830472984, 0, 0, 0, 0, 0, 0, 0, 0)
    row_b = struct.pack("<QLLQQQQLLQ", 2, 12345, 0, 0, 0, 0, 0, 0, 0, 0)

    summary = summarize_coreprofile_chunk(row_a + row_b + row_a, target_code=830472984)

    assert summary["byte_count"] == len(row_a) * 3
    assert summary["row_count"] == 3
    assert summary["target_event_count"] == 2
    assert summary["top_event_codes"][0] == {"code": 830472984, "count": 2}


def test_collector_start_failure_closes_owned_services_without_raw_text():
    service = FakeAsyncService()

    class FailingCollectorAdapter(PymobiledeviceIOSAdapter):
        async def _start_sysmontap(self):
            self._owned_services.append(service)
            raise RuntimeError("InvalidService com.apple.instruments.server.services.sysmontap")

    adapter = FailingCollectorAdapter()

    with pytest.raises(OperatorError) as exc_info:
        adapter.start_collectors(123)

    assert exc_info.value.code == "ios_developer_services_unavailable"
    assert "InvalidService" not in exc_info.value.message
    assert service.close_calls == 1
    assert adapter._owned_services == []
    assert adapter._active_pid is None
