from __future__ import annotations

from typing import Any

from perfengine.app.errors import OperatorError
from perfengine.app.models import PhoneStatus, Platform
from perfengine.ios.pymobiledevice import PymobiledeviceIOSAdapter
from perfengine.ios.tooling import IOSTooling
from perfengine.ios.tunnel import IOSTunnelManager


class IOSClient:
    def __init__(self, tooling: IOSTooling | None = None, tunnel_manager=None, runner=None, device_adapter=None) -> None:
        self.tooling = tooling or IOSTooling()
        self.tunnel_manager = tunnel_manager or IOSTunnelManager(self.tooling)
        self.runner = runner
        self.device_adapter = device_adapter or PymobiledeviceIOSAdapter()
        self._active_apps: set[tuple[str, str]] = set()

    def prepare(self, device_id: str, *, os_version: str | None = None) -> None:
        self.tunnel_manager.ensure_ready(device_id, os_version=os_version)
        tunnel_info_url = (
            getattr(self.tunnel_manager, "tunnel_info_url", None)
            if self.tunnel_manager.requires_tunnel(os_version)
            else None
        )
        self.device_adapter.connect(device_id, tunnel_info_url=tunnel_info_url)
        self.device_adapter.prepare_developer_services()

    def list_apps(self, device_id: str) -> list[dict[str, Any]]:
        return self.device_adapter.list_apps(device_id)

    def get_phone_status(self, device_id: str, package_name: str) -> PhoneStatus:
        try:
            process_status = self.device_adapter.get_process_status(package_name)
        except OperatorError as exc:
            if exc.code == "ios_device_disconnected":
                return PhoneStatus(
                    platform=Platform.IOS,
                    connection_state="disconnected",
                    device_label=device_id,
                    app_state="unknown",
                )
            raise
        app_state = "running"
        if not process_status.running:
            app_state = "exited" if (device_id, package_name) in self._active_apps else "not_running"
        return PhoneStatus(
            platform=Platform.IOS,
            connection_state="connected",
            device_label=device_id,
            app_state=app_state,
        )

    def start_collectors(self, device_id: str, package_name: str) -> None:
        process_status = self.device_adapter.get_process_status(package_name)
        if not process_status.running or process_status.pid is None:
            raise OperatorError(
                code="ios_app_not_running",
                message="Target iOS app is not running. Launch the app and try again.",
            )
        self.device_adapter.start_collectors(process_status.pid)
        self._active_apps.add((device_id, package_name))

    def stop_collectors(self, device_id: str, package_name: str) -> None:
        self._active_apps.discard((device_id, package_name))
        self.device_adapter.stop_collectors()

    def read_fps_sample(self, device_id: str, package_name: str) -> dict[str, Any]:
        return self.device_adapter.read_fps_sample()

    def read_system_sample(self, device_id: str, package_name: str) -> dict[str, Any]:
        snapshot = self.device_adapter.read_system_sample()
        return {
            "app_cpu_percent": snapshot.app_cpu_percent,
            "total_cpu_percent": snapshot.total_cpu_percent,
            "physFootprint": snapshot.phys_footprint,
            "memory_mb": snapshot.memory_mb,
        }

    def read_battery_sample(self, device_id: str) -> dict[str, Any]:
        snapshot = self.device_adapter.read_battery_sample()
        return {
            "battery_level": snapshot.battery_level,
            "temperature_c": snapshot.temperature_c,
        }
