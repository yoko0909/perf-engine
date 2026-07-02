from __future__ import annotations

from typing import Any

from perfengine.app.models import DeviceInfo, Platform
from perfengine.ios.pymobiledevice import PymobiledeviceIOSAdapter


class IOSDeviceProvider:
    def __init__(self, tooling=None, runner=None, device_adapter=None) -> None:
        self.tooling = tooling
        self.runner = runner
        self.device_adapter = device_adapter or PymobiledeviceIOSAdapter()

    def list_devices(self) -> list[DeviceInfo]:
        raw_devices = self.device_adapter.list_devices()
        devices = [self._to_device_info(item) for item in raw_devices]
        return [device for device in devices if device is not None]

    @classmethod
    def _to_device_info(cls, item: dict[str, Any]) -> DeviceInfo | None:
        device_id = cls._device_id_from(item)
        if not device_id:
            return None
        display_name = cls._first_text(
            item,
            "Name",
            "DeviceName",
            "deviceName",
            "ProductName",
            "ProductType",
            default=device_id,
        )
        connection_type = cls._first_text(
            item,
            "ConnectionType",
            "connectionType",
            "Transport",
            default="usb",
        ).lower()
        return DeviceInfo(
            device_id=device_id,
            display_name=display_name,
            connection_type=connection_type,
            platform=Platform.IOS,
            os_version=cls._first_text(item, "ProductVersion", "product_version", default="") or None,
        )

    @staticmethod
    def _device_id_from(item: dict[str, Any]) -> str:
        return IOSDeviceProvider._first_text(
            item,
            "Identifier",
            "UniqueDeviceID",
            "DeviceID",
            "UDID",
            "Udid",
            "udid",
            "deviceId",
            default="",
        )

    @staticmethod
    def _first_text(item: dict[str, Any], *keys: str, default: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default
