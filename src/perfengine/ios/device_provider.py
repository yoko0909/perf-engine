from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from perfengine.app.errors import OperatorError
from perfengine.app.models import DeviceInfo, Platform
from perfengine.ios.tooling import IOSTooling


@dataclass(slots=True)
class IOSCommandResult:
    returncode: int
    stdout: str | None
    stderr: str | None = ""


class IOSDeviceProvider:
    def __init__(self, tooling: IOSTooling, runner=None) -> None:
        self.tooling = tooling
        self.runner = runner or self._default_runner

    @staticmethod
    def _default_runner(cmd: list[str]) -> IOSCommandResult:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return IOSCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def list_devices(self) -> list[DeviceInfo]:
        paths = self.tooling.require_tools()
        try:
            completed = self.runner([str(paths.ios), "list", "--details"])
        except FileNotFoundError as exc:
            raise OperatorError(
                code="ios_tools_missing",
                message="iOS bundled tools are missing. Reinstall the tool package.",
            ) from exc

        if completed.returncode != 0:
            self._raise_command_error(completed.stderr or completed.stdout)

        return self._parse_devices(completed.stdout or "")

    @classmethod
    def _parse_devices(cls, stdout: str) -> list[DeviceInfo]:
        if not stdout.strip():
            return []
        try:
            payload = cls._load_device_payload(stdout)
        except json.JSONDecodeError as exc:
            raise OperatorError(
                code="ios_device_list_invalid",
                message="iOS device discovery returned unreadable data.",
            ) from exc

        raw_devices = cls._extract_device_items(payload)
        devices = [cls._to_device_info(item) for item in raw_devices]
        return [device for device in devices if device is not None]

    @staticmethod
    def _load_device_payload(stdout: str) -> Any:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            payloads = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            for payload in payloads:
                if isinstance(payload, dict) and any(
                    key in payload for key in ("devices", "deviceList", "DeviceList")
                ):
                    return payload
            if payloads:
                return payloads[-1]
            raise

    @staticmethod
    def _extract_device_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("devices", "deviceList", "DeviceList"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload] if IOSDeviceProvider._device_id_from(payload) else []

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

    @staticmethod
    def _raise_command_error(output: str) -> None:
        normalized = output.lower()
        if "trust" in normalized or "pair" in normalized:
            raise OperatorError(
                code="ios_device_not_trusted",
                message="iPhone is connected but not trusted. Unlock the iPhone and trust this computer.",
            )
        raise OperatorError(
            code="ios_device_list_failed",
            message="iOS device discovery failed. Reconnect the iPhone and try again.",
        )
