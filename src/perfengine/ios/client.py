from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from perfengine.app.errors import OperatorError
from perfengine.app.models import PhoneStatus, Platform
from perfengine.ios.tooling import IOSTooling
from perfengine.ios.tunnel import IOSTunnelManager


@dataclass(slots=True)
class IOSCommandResult:
    returncode: int
    stdout: str | None
    stderr: str | None = ""


class IOSClient:
    def __init__(self, tooling: IOSTooling | None = None, tunnel_manager=None, runner=None) -> None:
        self.tooling = tooling or IOSTooling()
        self.tunnel_manager = tunnel_manager or IOSTunnelManager(self.tooling)
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
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return IOSCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def prepare(self, device_id: str, *, os_version: str | None = None) -> None:
        self.tunnel_manager.ensure_ready(device_id, os_version=os_version)

    def list_apps(self, device_id: str) -> list[dict[str, Any]]:
        paths = self.tooling.require_tools()
        completed = self.runner([str(paths.sib), "app", "list", "-u", device_id, "-j"])
        if completed.returncode != 0:
            raise OperatorError(
                code="ios_app_list_failed",
                message="iOS app list could not be loaded. Unlock the iPhone and try again.",
            )
        return self._parse_app_list(completed.stdout)

    def get_phone_status(self, device_id: str, package_name: str) -> PhoneStatus:
        return PhoneStatus(
            platform=Platform.IOS,
            connection_state="connected",
            device_label=device_id,
            app_state="running",
        )

    def start_collectors(self, device_id: str, package_name: str) -> None:
        return None

    def stop_collectors(self, device_id: str, package_name: str) -> None:
        return None

    def read_fps_sample(self, device_id: str, package_name: str) -> dict[str, Any]:
        return {}

    def read_system_sample(self, device_id: str, package_name: str) -> dict[str, Any]:
        return {}

    def read_battery_sample(self, device_id: str) -> dict[str, Any]:
        return {}

    @staticmethod
    def _parse_app_list(stdout: str | None) -> list[dict[str, Any]]:
        stdout = stdout or ""
        if not stdout.strip():
            return []
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            try:
                return [json.loads(line) for line in stdout.splitlines() if line.strip()]
            except json.JSONDecodeError:
                raise OperatorError(
                    code="ios_app_list_invalid",
                    message="iOS app list returned unreadable data.",
                ) from exc
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("apps", "appList", "ApplicationList"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []
