import pytest

from perfengine.app.errors import OperatorError
from perfengine.app.models import PhoneStatus, Platform
from perfengine.ios.sampler import IOSSampler


class FakeIOSClient:
    def __init__(self):
        self.prepared = []
        self.started = []
        self.stopped = []
        self.status = PhoneStatus(
            platform=Platform.IOS,
            connection_state="connected",
            device_label="QA iPhone",
            app_state="running",
        )
        self.fps_sample = {"fps": 60.0}
        self.system_sample = {"app_cpu_percent": 8.0, "total_cpu_percent": 42.0, "physFootprint": 104857600}
        self.battery_sample = {"temperature_c": 32.0, "battery_level": 90}
        self.system_error = None
        self.status_after_system_error = None

    def prepare(self, device_id: str, *, os_version: str | None = None):
        self.prepared.append((device_id, os_version))

    def get_phone_status(self, device_id: str, package_name: str):
        return self.status

    def start_collectors(self, device_id: str, package_name: str):
        self.started.append((device_id, package_name))

    def stop_collectors(self, device_id: str, package_name: str):
        self.stopped.append((device_id, package_name))

    def read_fps_sample(self, device_id: str, package_name: str):
        return self.fps_sample

    def read_system_sample(self, device_id: str, package_name: str):
        if self.system_error is not None:
            if self.status_after_system_error is not None:
                self.status = self.status_after_system_error
            raise self.system_error
        return self.system_sample

    def read_battery_sample(self, device_id: str):
        return self.battery_sample


def test_sampler_begin_read_stop():
    client = FakeIOSClient()
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    sampler.begin("UDID1", "com.example.app")
    status, point = sampler.read("UDID1", "com.example.app")
    sampler.stop()

    assert client.prepared == [("UDID1", None)]
    assert client.started == [("UDID1", "com.example.app")]
    assert client.stopped == [("UDID1", "com.example.app")]
    assert status.platform is Platform.IOS
    assert point is not None
    assert point.fps == 60.0
    assert point.memory_mb == 100.0


def test_sampler_begin_passes_os_version_to_client_prepare():
    client = FakeIOSClient()
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    sampler.begin("UDID1", "com.example.app", os_version="15.0")

    assert client.prepared == [("UDID1", "15.0")]


def test_sampler_waits_when_ios_sample_has_not_arrived():
    client = FakeIOSClient()
    client.fps_sample = {}
    client.system_sample = {}
    client.battery_sample = {}
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    sampler.begin("UDID1", "com.example.app")
    status, point = sampler.read("UDID1", "com.example.app")

    assert point is None
    assert status.status_notice == "Waiting for iOS data."


def test_sampler_keeps_running_when_partial_ios_metrics_are_missing():
    client = FakeIOSClient()
    client.fps_sample = {"fps": 55.0}
    client.system_sample = {"physFootprint": None}
    client.battery_sample = {}
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    sampler.begin("UDID1", "com.example.app")
    status, point = sampler.read("UDID1", "com.example.app")

    assert status.app_state == "running"
    assert status.status_notice == "Some iOS metrics are unavailable."
    assert point is not None
    assert point.fps == 55.0
    assert point.memory_mb is None


def test_sampler_reports_app_exit_without_metric_point():
    client = FakeIOSClient()
    client.status = PhoneStatus(
        platform=Platform.IOS,
        connection_state="connected",
        device_label="QA iPhone",
        app_state="exited",
    )
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    status, point = sampler.read("UDID1", "com.example.app")

    assert status.app_state == "exited"
    assert point is None


def test_sampler_begin_fails_when_app_is_not_running():
    client = FakeIOSClient()
    client.status = PhoneStatus(
        platform=Platform.IOS,
        connection_state="connected",
        device_label="QA iPhone",
        app_state="not_running",
    )
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    with pytest.raises(OperatorError) as exc_info:
        sampler.begin("UDID1", "com.example.app")

    assert exc_info.value.code == "ios_app_not_running"


def test_sampler_begin_fails_when_iphone_is_disconnected():
    client = FakeIOSClient()
    client.status = PhoneStatus(
        platform=Platform.IOS,
        connection_state="disconnected",
        device_label="QA iPhone",
        app_state="unknown",
    )
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")

    with pytest.raises(OperatorError) as exc_info:
        sampler.begin("UDID1", "com.example.app")

    assert exc_info.value.code == "ios_device_disconnected"


def test_sampler_read_stops_points_when_iphone_disconnects():
    client = FakeIOSClient()
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")
    sampler.begin("UDID1", "com.example.app")
    client.status = PhoneStatus(
        platform=Platform.IOS,
        connection_state="disconnected",
        device_label="QA iPhone",
        app_state="unknown",
    )

    status, point = sampler.read("UDID1", "com.example.app")

    assert status.connection_state == "disconnected"
    assert point is None


def test_sampler_keeps_running_when_collector_read_fails_but_status_is_healthy():
    client = FakeIOSClient()
    client.system_error = OperatorError(
        code="ios_developer_services_unavailable",
        message="iOS developer services are unavailable. Reconnect the iPhone and try again.",
    )
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")
    sampler.begin("UDID1", "com.example.app")

    status, point = sampler.read("UDID1", "com.example.app")

    assert status.connection_state == "connected"
    assert status.app_state == "running"
    assert status.status_notice == "Some iOS metrics are unavailable."
    assert point is None


def test_sampler_returns_interrupted_status_when_collector_read_fails_after_disconnect():
    client = FakeIOSClient()
    client.system_error = OperatorError(
        code="ios_device_disconnected",
        message="iPhone is not connected. Reconnect it and try again.",
    )
    client.status_after_system_error = PhoneStatus(
        platform=Platform.IOS,
        connection_state="disconnected",
        device_label="QA iPhone",
        app_state="unknown",
    )
    sampler = IOSSampler(client, timestamp_factory=lambda: "2026-05-07T00:00:00Z")
    sampler.begin("UDID1", "com.example.app")

    status, point = sampler.read("UDID1", "com.example.app")

    assert status.connection_state == "disconnected"
    assert point is None

