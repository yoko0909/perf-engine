from perfengine.app.models import PhoneStatus
from perfengine.ios.metrics import normalize_ios_metric_point


def test_normalize_ios_metric_point_maps_demo_style_fields():
    status = PhoneStatus(
        battery_level=88,
        temperature_c=34.5,
    )

    point = normalize_ios_metric_point(
        timestamp="2026-05-07T00:00:00Z",
        fps_sample={"fps": 50.0},
        system_sample={
            "app_cpu_percent": 12.5,
            "total_cpu_percent": 43.0,
            "physFootprint": 268435456,
        },
        battery_sample={"temperature_c": 35.0, "battery_level": 87},
        status=status,
    )

    assert point is not None
    assert point.fps == 50.0
    assert point.frame_time_ms == 20.0
    assert point.app_cpu_percent == 12.5
    assert point.total_cpu_percent == 43.0
    assert point.memory_mb == 256.0
    assert point.temperature_c == 35.0
    assert point.battery_level == 87


def test_normalize_ios_metric_point_keeps_missing_metrics_null():
    point = normalize_ios_metric_point(
        timestamp="2026-05-07T00:00:00Z",
        fps_sample={"fps": None},
        system_sample={"app_cpu_percent": 6.5, "physFootprint": None},
        battery_sample={},
        status=PhoneStatus(),
    )

    assert point is not None
    assert point.app_cpu_percent == 6.5
    assert point.fps is None
    assert point.frame_time_ms is None
    assert point.memory_mb is None
    assert point.temperature_c is None


def test_normalize_ios_metric_point_returns_none_when_all_metrics_are_missing():
    point = normalize_ios_metric_point(
        timestamp="2026-05-07T00:00:00Z",
        fps_sample={},
        system_sample={},
        battery_sample={},
        status=PhoneStatus(),
    )

    assert point is None
