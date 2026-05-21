from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import urlopen as default_urlopen

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSTooling


class TunnelProbe(Protocol):
    def __call__(self, device_id: str) -> bool:
        ...


@dataclass(slots=True)
class TunnelProcess:
    process: object

    def stop(self) -> None:
        terminate = getattr(self.process, "terminate", None)
        if terminate is not None:
            terminate()


class IOSTunnelManager:
    """Manages the Windows host-side tunnel process; nothing is installed on the iPhone."""

    def __init__(
        self,
        tooling: IOSTooling,
        *,
        popen=None,
        probe: TunnelProbe | None = None,
        urlopen=None,
        sleep=None,
        timeout_s: float = 10.0,
        poll_interval_s: float = 0.25,
        tunnel_info_url: str = "http://127.0.0.1:60105/tunnels",
    ) -> None:
        self.tooling = tooling
        self.popen = popen or self._default_popen
        self.urlopen = urlopen or default_urlopen
        self.tunnel_info_url = tunnel_info_url
        self.probe = probe or self._probe_http_tunnel
        self.sleep = sleep or time.sleep
        self.timeout_s = timeout_s
        self.poll_interval_s = poll_interval_s
        self._process: TunnelProcess | None = None

    @staticmethod
    def requires_tunnel(os_version: str | None) -> bool:
        if not os_version:
            return True
        try:
            major = int(os_version.split(".", 1)[0])
        except ValueError:
            return True
        return major >= 17

    @staticmethod
    def _default_popen(cmd: list[str]):
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _probe_http_tunnel(self, device_id: str) -> bool:
        try:
            response = self.urlopen(self.tunnel_info_url, timeout=1.0)
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except (OSError, URLError, json.JSONDecodeError):
            return False

        if isinstance(payload, dict):
            if device_id in payload:
                return True
            tunnels = payload.get("tunnels")
            if isinstance(tunnels, list):
                return self._payload_contains_device(tunnels, device_id)
        if isinstance(payload, list):
            return self._payload_contains_device(payload, device_id)
        return False

    @staticmethod
    def _payload_contains_device(items, device_id: str) -> bool:
        for item in items:
            if isinstance(item, dict) and item.get("udid") == device_id:
                return True
        return False

    def ensure_ready(self, device_id: str, *, os_version: str | None = None) -> None:
        if not self.requires_tunnel(os_version):
            return
        if self.probe(device_id):
            return
        if self._process is None:
            self.start()
        if not self._wait_ready(device_id):
            self.stop()
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS tunnel could not be started. Reconnect the iPhone and try again.",
            )

    def start(self) -> None:
        paths = self.tooling.require_tools()
        try:
            process = self.popen([str(paths.ios), "tunnel", "start", "--userspace"])
        except OSError as exc:
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS tunnel could not be started. Reconnect the iPhone and try again.",
            ) from exc
        self._process = TunnelProcess(process)

    def stop(self) -> None:
        if self._process is not None:
            self._process.stop()
            self._process = None

    def _wait_ready(self, device_id: str) -> bool:
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            if self.probe(device_id):
                return True
            self.sleep(self.poll_interval_s)
        return False
