from __future__ import annotations

from dataclasses import dataclass

from perfengine.app.errors import OperatorError
from perfengine.app.models import DeviceInfo, Platform


@dataclass(slots=True)
class PlatformBackend:
    device_provider: object
    app_provider: object
    collector: object


class PlatformRegistry:
    def __init__(self) -> None:
        self._backends: dict[Platform, PlatformBackend] = {}
        self._devices: dict[str, DeviceInfo] = {}

    def register(self, platform: Platform, *, provider=None, device_provider=None, app_provider=None, collector) -> None:
        device_provider = device_provider or provider
        app_provider = app_provider or provider
        self._backends[platform] = PlatformBackend(
            device_provider=device_provider,
            app_provider=app_provider,
            collector=collector,
        )

    def list_devices(self) -> list[DeviceInfo]:
        devices: list[DeviceInfo] = []
        errors: list[OperatorError] = []
        for platform, backend in self._backends.items():
            try:
                for device in backend.device_provider.list_devices():
                    device.platform = platform
                    devices.append(device)
            except OperatorError as exc:
                errors.append(exc)

        self._devices = {device.device_id: device for device in devices}
        if not devices and errors:
            raise errors[0]
        return devices

    def platform_for_device(self, device_id: str) -> Platform:
        try:
            return self._devices[device_id].platform
        except KeyError as exc:
            raise OperatorError(
                code="device_not_found",
                message="Device is no longer available.",
            ) from exc

    def provider_for_device(self, device_id: str):
        return self._backends[self.platform_for_device(device_id)].app_provider

    def collector_for_device(self, device_id: str):
        return self._backends[self.platform_for_device(device_id)].collector
