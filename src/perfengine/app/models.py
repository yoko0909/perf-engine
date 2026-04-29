from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionPhase(str, Enum):
    IDLE = "idle"
    LOADING_DEVICES = "loading_devices"
    LOADING_APPS = "loading_apps"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    display_name: str
    connection_type: str = "usb"


@dataclass(slots=True)
class AppInfo:
    package_name: str
    display_name: str
    pid: int | None = None


@dataclass(slots=True)
class SessionState:
    phase: SessionPhase
    selected_device_id: str | None = None
    selected_package: str | None = None
    selectors_locked: bool = False
    message: str = ""


@dataclass(slots=True)
class PhoneStatus:
    connection_state: str = "disconnected"
    device_label: str = ""
    screen_state: str = "unknown"
    app_state: str = "not_selected"
    battery_level: int | None = None
    temperature_c: float | None = None
    last_updated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class MetricPoint:
    timestamp: str
    fps: float | None = None
    frame_time_ms: float | None = None
    app_cpu_percent: float | None = None
    total_cpu_percent: float | None = None
    memory_mb: float | None = None
    temperature_c: float | None = None
    battery_level: int | None = None


@dataclass(slots=True)
class LiveSnapshot:
    session: SessionState
    status: PhoneStatus
    metrics: list[MetricPoint] = field(default_factory=list)
