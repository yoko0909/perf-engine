from __future__ import annotations

import re

from perfengine.app.models import MetricPoint, PhoneStatus


def normalize_metric_point(
    *,
    timestamp: str,
    package_name: str,
    cpu_output: str,
    memory_output: str,
    frame_output: str,
    status: PhoneStatus,
) -> MetricPoint | None:
    total_cpu, app_cpu = parse_cpu_usage(cpu_output, package_name)
    memory_mb = parse_memory_mb(memory_output)
    fps, frame_time_ms = parse_frame_stats(frame_output)

    point = MetricPoint(
        timestamp=timestamp,
        fps=fps,
        frame_time_ms=frame_time_ms,
        app_cpu_percent=app_cpu,
        total_cpu_percent=total_cpu,
        memory_mb=memory_mb,
        temperature_c=status.temperature_c,
        battery_level=status.battery_level,
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


def parse_cpu_usage(output: str, package_name: str) -> tuple[float | None, float | None]:
    total_match = re.search(r"([\d.]+)%\s+TOTAL", output, re.IGNORECASE)
    app_pattern = re.compile(
        rf"([\d.]+)%\s+(?:\d+/)?{re.escape(package_name)}(?::|\s|$)",
        re.IGNORECASE,
    )
    app_match = app_pattern.search(output)
    total_cpu = float(total_match.group(1)) if total_match else None
    app_cpu = float(app_match.group(1)) if app_match else None
    return total_cpu, app_cpu


def parse_memory_mb(output: str) -> float | None:
    for pattern in (r"TOTAL PSS:\s*([\d,]+)", r"TOTAL:\s*([\d,]+)"):
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value_kb = int(match.group(1).replace(",", ""))
            return round(value_kb / 1024, 2)
    return None


def parse_frame_stats(output: str) -> tuple[float | None, float | None]:
    fps_match = re.search(r"(?:Average\s+FPS|FPS):\s*([\d.]+)", output, re.IGNORECASE)
    frame_match = re.search(
        r"(?:Average\s+frame\s+time|Frame\s+time):\s*([\d.]+)\s*ms",
        output,
        re.IGNORECASE,
    )
    fps = float(fps_match.group(1)) if fps_match else None
    frame_time_ms = float(frame_match.group(1)) if frame_match else None
    return fps, frame_time_ms
