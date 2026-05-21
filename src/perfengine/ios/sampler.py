from __future__ import annotations

from collections.abc import Callable

from perfengine.app.errors import OperatorError
from perfengine.app.models import PhoneStatus, Platform, utc_now_iso
from perfengine.ios.metrics import normalize_ios_metric_point


class IOSSampler:
    def __init__(self, ios_client, *, timestamp_factory: Callable[[], str] = utc_now_iso) -> None:
        self.ios_client = ios_client
        self.timestamp_factory = timestamp_factory
        self._active_session: tuple[str, str] | None = None

    def begin(self, device_id: str, package_name: str) -> None:
        self.ios_client.prepare(device_id)
        status = self._status(device_id, package_name)
        if status.connection_state != "connected":
            raise OperatorError(
                code="ios_device_disconnected",
                message="iPhone is not connected. Reconnect it and try again.",
            )
        if status.app_state != "running":
            raise OperatorError(
                code="ios_app_not_running",
                message="Target iOS app is not running. Launch the app and try again.",
            )
        self.ios_client.start_collectors(device_id, package_name)
        self._active_session = (device_id, package_name)

    def stop(self) -> None:
        if self._active_session is not None:
            device_id, package_name = self._active_session
            self.ios_client.stop_collectors(device_id, package_name)
            self._active_session = None

    def read(self, device_id: str, package_name: str):
        status = self._status(device_id, package_name)
        if status.connection_state != "connected" or status.app_state != "running":
            return status, None

        fps_sample = self.ios_client.read_fps_sample(device_id, package_name)
        system_sample = self.ios_client.read_system_sample(device_id, package_name)
        battery_sample = self.ios_client.read_battery_sample(device_id)
        point = normalize_ios_metric_point(
            timestamp=self.timestamp_factory(),
            fps_sample=fps_sample,
            system_sample=system_sample,
            battery_sample=battery_sample,
            status=status,
        )
        if point is None:
            status.status_notice = "Waiting for iOS data."
            return status, None
        if self._has_unavailable_metrics(point):
            status.status_notice = "Some iOS metrics are unavailable."
        return status, point

    def _status(self, device_id: str, package_name: str) -> PhoneStatus:
        status = self.ios_client.get_phone_status(device_id, package_name)
        status.platform = Platform.IOS
        return status

    @staticmethod
    def _has_unavailable_metrics(point) -> bool:
        return any(
            value is None
            for value in (
                point.fps,
                point.frame_time_ms,
                point.app_cpu_percent,
                point.total_cpu_percent,
                point.memory_mb,
                point.temperature_c,
                point.battery_level,
            )
        )

