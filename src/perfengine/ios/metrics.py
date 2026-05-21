from __future__ import annotations

from typing import Any

from perfengine.app.models import MetricPoint, PhoneStatus


def normalize_ios_metric_point(
    *,
    timestamp: str,
    fps_sample: dict[str, Any] | None,
    system_sample: dict[str, Any] | None,
    battery_sample: dict[str, Any] | None,
    status: PhoneStatus,
) -> MetricPoint | None:
    fps_sample = fps_sample or {}
    system_sample = system_sample or {}
    battery_sample = battery_sample or {}

    fps = _first_number(fps_sample, "fps", "FPS", "current_fps")
    frame_time_ms = _first_number(fps_sample, "frame_time_ms", "frameTimeMs", "frame_time")
    if frame_time_ms is None and fps and fps > 0:
        frame_time_ms = round(1000.0 / fps, 3)

    memory_mb = _memory_mb(system_sample)
    temperature_c = _first_number(battery_sample, "temperature_c", "temperatureC", "Temperature")
    if temperature_c is None:
        temperature_c = status.temperature_c

    battery_level = _first_int(battery_sample, "battery_level", "batteryLevel", "level")
    if battery_level is None:
        battery_level = status.battery_level

    point = MetricPoint(
        timestamp=timestamp,
        fps=fps,
        frame_time_ms=frame_time_ms,
        app_cpu_percent=_first_number(system_sample, "app_cpu_percent", "appCpuPercent", "appCPU"),
        total_cpu_percent=_first_number(system_sample, "total_cpu_percent", "totalCpuPercent", "totalCPU"),
        memory_mb=memory_mb,
        temperature_c=temperature_c,
        battery_level=battery_level,
    )
    if all(
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
    ):
        return None
    return point


def _memory_mb(sample: dict[str, Any]) -> float | None:
    direct = _first_number(sample, "memory_mb", "memoryMB", "physFootprintMB")
    if direct is not None:
        return direct
    footprint = _first_number(sample, "physFootprint", "physicalFootprint", "phys_footprint")
    if footprint is None:
        return None
    return round(footprint / 1024 / 1024, 3)


def _first_number(sample: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = sample.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(sample: dict[str, Any], *keys: str) -> int | None:
    value = _first_number(sample, *keys)
    if value is None:
        return None
    return int(value)

