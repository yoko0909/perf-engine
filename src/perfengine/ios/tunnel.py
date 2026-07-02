from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import urlopen as default_urlopen

from perfengine.app.errors import OperatorError


class TunnelProbe(Protocol):
    def __call__(self, device_id: str) -> bool:
        ...


class TunnelStarter(Protocol):
    def __call__(self) -> object:
        ...


@dataclass(slots=True)
class TunnelProcess:
    process: object

    def stop(self) -> None:
        stop = getattr(self.process, "stop", None)
        if stop is not None:
            stop()
            return
        terminate = getattr(self.process, "terminate", None)
        if terminate is not None:
            terminate()


class IOSTunnelManager:
    """Manages the Windows host-side tunnel process; nothing is installed on the iPhone."""

    def __init__(
        self,
        tooling=None,
        *,
        popen=None,
        starter: TunnelStarter | None = None,
        probe: TunnelProbe | None = None,
        urlopen=None,
        sleep=None,
        timeout_s: float = 10.0,
        poll_interval_s: float = 0.25,
        tunnel_info_url: str = "http://127.0.0.1:60105/tunnels",
    ) -> None:
        self.tooling = tooling
        self.popen = popen
        self.starter = starter or self._default_starter
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
        if self._process is None:
            self.start()
        if self.probe(device_id):
            return
        if not self._wait_ready(device_id):
            self.stop()
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS tunnel could not be started. Reconnect the iPhone and try again.",
            )

    def start(self) -> None:
        try:
            process = self.starter()
        except OSError as exc:
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS pymobiledevice tunnel could not be started. Reconnect the iPhone and try again.",
            ) from exc
        except Exception as exc:
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS pymobiledevice tunnel could not be started. Reconnect the iPhone and try again.",
            ) from exc
        if isinstance(process, str):
            self.tunnel_info_url = process
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

    @staticmethod
    def _default_starter() -> str:
        return _start_pymobiledevice_tunneld()


_TUNNELD_HOST = "127.0.0.1"
_TUNNELD_PORT: int | None = None
_TUNNELD_THREAD: threading.Thread | None = None
_TUNNELD_LOCK = threading.Lock()


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _find_free_port(host: str = _TUNNELD_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _current_tunneld_url() -> str | None:
    if _TUNNELD_PORT is None:
        return None
    if not _is_port_open(_TUNNELD_HOST, _TUNNELD_PORT):
        return None
    return f"http://{_TUNNELD_HOST}:{_TUNNELD_PORT}"


def _run_tunneld(host: str, port: int) -> None:
    from pymobiledevice3.remote.common import TunnelProtocol
    from pymobiledevice3.tunneld.server import TunneldRunner

    TunneldRunner.create(
        host,
        port,
        protocol=TunnelProtocol.DEFAULT,
        usb_monitor=True,
        wifi_monitor=False,
        usbmux_monitor=True,
        mobdev2_monitor=True,
    )


def _start_pymobiledevice_tunneld(*, port: int | None = None) -> str:
    current_url = _current_tunneld_url()
    if current_url:
        return current_url

    with _TUNNELD_LOCK:
        current_url = _current_tunneld_url()
        if current_url:
            return current_url

        selected_port = port
        if selected_port is None or _is_port_open(_TUNNELD_HOST, selected_port):
            selected_port = _find_free_port(_TUNNELD_HOST)

        global _TUNNELD_PORT, _TUNNELD_THREAD
        _TUNNELD_PORT = selected_port
        _TUNNELD_THREAD = threading.Thread(
            target=_run_tunneld,
            args=(_TUNNELD_HOST, selected_port),
            daemon=True,
            name="ios_tunneld",
        )
        _TUNNELD_THREAD.start()

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        current_url = _current_tunneld_url()
        if current_url:
            return current_url
        if _TUNNELD_THREAD is not None and not _TUNNELD_THREAD.is_alive():
            break
        time.sleep(0.2)
    raise RuntimeError("pymobiledevice3 tunneld failed to start")
