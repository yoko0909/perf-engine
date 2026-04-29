from __future__ import annotations

from perfengine.app.models import DeviceInfo


class DeviceProvider:
    def __init__(self, adb_client) -> None:
        self.adb_client = adb_client

    def list_devices(self) -> list[DeviceInfo]:
        output = self.adb_client.run(["devices", "-l"])
        devices: list[DeviceInfo] = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2 or parts[1] != "device":
                continue
            device_id = parts[0]
            model = self._extract_model(parts) or device_id
            connection_type = "wifi" if ":" in device_id else "usb"
            devices.append(
                DeviceInfo(
                    device_id=device_id,
                    display_name=model,
                    connection_type=connection_type,
                )
            )
        return devices

    @staticmethod
    def _extract_model(parts: list[str]) -> str | None:
        for part in parts:
            if part.startswith("model:"):
                return part.split(":", 1)[1]
        for part in parts:
            if part.startswith("product:"):
                return part.split(":", 1)[1]
        return None
