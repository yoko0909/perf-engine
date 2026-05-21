# iOS MVP Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add iOS device support to the validated Android MVP workflow: discover iPhones from Windows, list apps, start/stop one iOS session, and show Android-aligned live charts/status.

**Architecture:** Keep the current service/bridge/UI flow, but add platform-aware dispatch behind it. iOS-specific tooling, tunnel readiness, DVT adapters, and metric normalization stay in focused `perfengine.ios` modules so Android behavior remains unchanged.

**Tech Stack:** Python 3.11+, dataclasses, pywebview, Vue 3, Vite/Vitest, OpenSpec, bundled Windows-side iOS tooling inspired by `Perftool_Demo`.

---

## File Structure

Create:
- `src/perfengine/app/platforms.py`: platform enum plus provider registry/dispatcher.
- `src/perfengine/ios/__init__.py`: iOS package marker.
- `src/perfengine/ios/tooling.py`: product-owned iOS tool path and version/readiness checks.
- `src/perfengine/ios/device_provider.py`: iOS device discovery adapter.
- `src/perfengine/ios/app_provider.py`: user app listing adapter.
- `src/perfengine/ios/tunnel.py`: automatic Windows-host iOS tunnel preparation/readiness.
- `src/perfengine/ios/metrics.py`: iOS metric normalization into `MetricPoint`.
- `src/perfengine/ios/sampler.py`: iOS sampler lifecycle matching `begin/stop/read`.
- `tests/app/test_platform_dispatch.py`: service dispatch tests.
- `tests/ios/test_tooling.py`: bundled tool path/readiness tests.
- `tests/ios/test_device_provider.py`: device discovery tests.
- `tests/ios/test_app_provider.py`: app listing tests.
- `tests/ios/test_metrics.py`: iOS metric mapping tests.
- `tests/ios/test_sampler.py`: iOS lifecycle/status tests.
- `docs/manual-tests/ios-mvp-support.md`: manual verification checklist for the user.

Modify:
- `src/perfengine/app/models.py`: add platform fields and optional status notice.
- `src/perfengine/app/service.py`: dispatch by selected device platform; keep Android-compatible constructor path.
- `src/perfengine/main.py`: wire Android and iOS providers/samplers into the registry.
- `src/perfengine/ui/bridge.py`: no API name changes; ensure platform fields serialize.
- `ui/src/types.ts`: add platform fields and status notice type.
- `ui/src/state/sessionStore.ts`: show visible status prompts for missing/delayed iOS metrics.
- `ui/src/components/ToolbarPanel.vue`: show platform in device selector.
- `ui/src/components/StatusCard.vue`: render status notice/unknown states clearly.
- `ui/src/components/MetricChart.vue`: keep null values as gaps.
- Existing tests under `tests/app`, `tests/android`, `tests/ui`, and `ui/src/**/*.spec.ts`: update fixtures for platform fields.

Reference only:
- `Perftool_Demo/ios/IosUtils.py`
- `Perftool_Demo/ios/ios_perf_client.py`
- `Perftool_Demo/ios/ios_tunnel.py`
- `Perftool_Demo/ios/idevice/**`

---

### Task 1: Platform Model and Registry

**Files:**
- Modify: `src/perfengine/app/models.py`
- Create: `src/perfengine/app/platforms.py`
- Modify: `tests/app/test_service.py`
- Create: `tests/app/test_platform_dispatch.py`

- [ ] **Step 1: Write failing tests for platform fields**

Add to `tests/app/test_platform_dispatch.py`:

```python
from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, Platform, SessionPhase
from perfengine.app.platforms import PlatformRegistry
from perfengine.app.service import PerfToolService


class FakeProvider:
    def __init__(self, devices):
        self.devices = devices

    def list_devices(self):
        return self.devices

    def list_apps(self, device_id: str):
        return [AppInfo(package_name=f"{device_id}.app", display_name=f"{device_id}.app")]


class FakeCollector:
    def __init__(self, platform: Platform):
        self.platform = platform
        self.started = []

    def begin(self, device_id: str, package_name: str):
        self.started.append((device_id, package_name))

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        return (
            PhoneStatus(
                platform=self.platform,
                connection_state="connected",
                device_label=device_id,
                app_state="running",
            ),
            None,
        )


def test_registry_combines_android_and_ios_devices():
    registry = PlatformRegistry()
    registry.register(
        Platform.ANDROID,
        provider=FakeProvider([DeviceInfo(device_id="android-1", display_name="Pixel", platform=Platform.ANDROID)]),
        collector=FakeCollector(Platform.ANDROID),
    )
    registry.register(
        Platform.IOS,
        provider=FakeProvider([DeviceInfo(device_id="ios-1", display_name="iPhone", platform=Platform.IOS)]),
        collector=FakeCollector(Platform.IOS),
    )

    devices = registry.list_devices()

    assert [device.platform for device in devices] == [Platform.ANDROID, Platform.IOS]
    assert registry.platform_for_device("ios-1") is Platform.IOS


def test_service_dispatches_apps_and_collection_by_selected_platform():
    ios_collector = FakeCollector(Platform.IOS)
    registry = PlatformRegistry()
    registry.register(
        Platform.ANDROID,
        provider=FakeProvider([DeviceInfo(device_id="android-1", display_name="Pixel", platform=Platform.ANDROID)]),
        collector=FakeCollector(Platform.ANDROID),
    )
    registry.register(
        Platform.IOS,
        provider=FakeProvider([DeviceInfo(device_id="ios-1", display_name="iPhone", platform=Platform.IOS)]),
        collector=ios_collector,
    )
    service = PerfToolService(platform_registry=registry)

    service.list_devices()
    apps = service.list_apps("ios-1")
    state = service.start_session("ios-1", apps[0].package_name)

    assert apps[0].platform is Platform.IOS
    assert state.platform is Platform.IOS
    assert state.phase is SessionPhase.RUNNING
    assert ios_collector.started == [("ios-1", "ios-1.app")]
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
python -m pytest tests/app/test_platform_dispatch.py -q
```

Expected: fail because `Platform`, `PlatformRegistry`, `platform` fields, and `platform_registry` service constructor do not exist.

- [ ] **Step 3: Add platform fields**

In `src/perfengine/app/models.py`, add `Platform` and fields:

```python
class Platform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    display_name: str
    connection_type: str = "usb"
    platform: Platform = Platform.ANDROID


@dataclass(slots=True)
class AppInfo:
    package_name: str
    display_name: str
    pid: int | None = None
    platform: Platform = Platform.ANDROID


@dataclass(slots=True)
class SessionState:
    phase: SessionPhase
    selected_device_id: str | None = None
    selected_package: str | None = None
    selectors_locked: bool = False
    message: str = ""
    platform: Platform | None = None


@dataclass(slots=True)
class PhoneStatus:
    platform: Platform | None = None
    connection_state: str = "disconnected"
    device_label: str = ""
    screen_state: str = "unknown"
    app_state: str = "not_selected"
    battery_level: int | None = None
    temperature_c: float | None = None
    status_notice: str = ""
    last_updated_at: str = field(default_factory=utc_now_iso)
```

- [ ] **Step 4: Add registry**

Create `src/perfengine/app/platforms.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from perfengine.app.errors import OperatorError
from perfengine.app.models import DeviceInfo, Platform


@dataclass(slots=True)
class PlatformBackend:
    provider: object
    collector: object


class PlatformRegistry:
    def __init__(self) -> None:
        self._backends: dict[Platform, PlatformBackend] = {}
        self._devices: dict[str, DeviceInfo] = {}

    def register(self, platform: Platform, *, provider, collector) -> None:
        self._backends[platform] = PlatformBackend(provider=provider, collector=collector)

    def list_devices(self) -> list[DeviceInfo]:
        devices: list[DeviceInfo] = []
        errors: list[OperatorError] = []
        for platform, backend in self._backends.items():
            try:
                for device in backend.provider.list_devices():
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
            raise OperatorError(code="device_not_found", message="Device is no longer available.") from exc

    def provider_for_device(self, device_id: str):
        return self._backends[self.platform_for_device(device_id)].provider

    def collector_for_device(self, device_id: str):
        return self._backends[self.platform_for_device(device_id)].collector
```

- [ ] **Step 5: Update service constructor and dispatch**

Modify `src/perfengine/app/service.py` so it supports either old Android-only constructor arguments or a registry:

```python
def __init__(
    self,
    device_provider=None,
    app_provider=None,
    collector=None,
    *,
    platform_registry=None,
    history_limit: int = 60,
) -> None:
    self.platform_registry = platform_registry
    self.device_provider = device_provider
    self.app_provider = app_provider
    self.collector = collector
    self.history_limit = history_limit
    self.history = []
    self.status = PhoneStatus()
    self.state = SessionState(phase=SessionPhase.IDLE)
    self._devices_by_id: dict[str, str] = {}
```

In `list_devices()`, use:

```python
devices = (
    self.platform_registry.list_devices()
    if self.platform_registry is not None
    else self.device_provider.list_devices()
)
```

In `list_apps(device_id)`, use:

```python
provider = (
    self.platform_registry.provider_for_device(device_id)
    if self.platform_registry is not None
    else self.app_provider
)
apps = provider.list_apps(device_id)
platform = self.platform_registry.platform_for_device(device_id) if self.platform_registry is not None else None
for app in apps:
    if platform is not None:
        app.platform = platform
```

In `start_session()` and `_refresh_running_snapshot()`, resolve collector via helper:

```python
def _collector_for(self, device_id: str | None):
    if self.platform_registry is None or device_id is None:
        return self.collector
    return self.platform_registry.collector_for_device(device_id)
```

Then call `collector = self._collector_for(device_id)`.

- [ ] **Step 6: Run service tests**

Run:

```powershell
python -m pytest tests/app/test_service.py tests/app/test_platform_dispatch.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add src/perfengine/app/models.py src/perfengine/app/platforms.py src/perfengine/app/service.py tests/app/test_service.py tests/app/test_platform_dispatch.py
git commit -m "feat: add platform dispatch"
```

---

### Task 2: Bundled iOS Tooling and Device Discovery

**Files:**
- Create: `src/perfengine/ios/__init__.py`
- Create: `src/perfengine/ios/tooling.py`
- Create: `src/perfengine/ios/device_provider.py`
- Create: `tests/ios/test_tooling.py`
- Create: `tests/ios/test_device_provider.py`

- [ ] **Step 1: Write tooling tests**

Create `tests/ios/test_tooling.py`:

```python
from pathlib import Path

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSToolPaths


def test_tool_paths_resolve_from_product_assets(tmp_path: Path):
    asset_dir = tmp_path / "assets" / "ios"
    asset_dir.mkdir(parents=True)
    go_ios = asset_dir / "ios.exe"
    sib = asset_dir / "sib.exe"
    go_ios.write_text("", encoding="utf-8")
    sib.write_text("", encoding="utf-8")

    paths = IOSToolPaths(product_root=tmp_path)

    assert paths.go_ios_path == go_ios
    assert paths.sib_path == sib


def test_tool_paths_report_missing_assets(tmp_path: Path):
    paths = IOSToolPaths(product_root=tmp_path)

    with pytest.raises(OperatorError) as exc:
        paths.require_go_ios()

    assert exc.value.code == "ios_tool_missing"
    assert "iOS tool package is incomplete" in exc.value.message
```

- [ ] **Step 2: Write iOS discovery tests**

Create `tests/ios/test_device_provider.py`:

```python
import json
from pathlib import Path

import pytest

from perfengine.app.errors import OperatorError
from perfengine.app.models import Platform
from perfengine.ios.device_provider import IOSDeviceProvider
from perfengine.ios.tooling import IOSToolPaths


class Completed:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def make_paths(tmp_path: Path) -> IOSToolPaths:
    asset_dir = tmp_path / "assets" / "ios"
    asset_dir.mkdir(parents=True)
    (asset_dir / "ios.exe").write_text("", encoding="utf-8")
    (asset_dir / "sib.exe").write_text("", encoding="utf-8")
    return IOSToolPaths(product_root=tmp_path)


def test_ios_device_provider_parses_go_ios_output(tmp_path: Path):
    payload = {
        "deviceList": [
            {
                "Udid": "00008110-123",
                "ProductType": "iPhone15,3",
                "ProductVersion": "17.4",
            }
        ]
    }
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return Completed(json.dumps(payload))

    provider = IOSDeviceProvider(tool_paths=make_paths(tmp_path), runner=runner)
    devices = provider.list_devices()

    assert calls[0][0].name == "ios.exe"
    assert devices[0].device_id == "00008110-123"
    assert devices[0].display_name == "iPhone15,3 (iOS 17.4)"
    assert devices[0].platform is Platform.IOS


def test_ios_device_provider_turns_tool_failure_into_operator_error(tmp_path: Path):
    def runner(cmd, **kwargs):
        return Completed("", returncode=1)

    provider = IOSDeviceProvider(tool_paths=make_paths(tmp_path), runner=runner)

    with pytest.raises(OperatorError) as exc:
        provider.list_devices()

    assert exc.value.code == "ios_unavailable"
```

- [ ] **Step 3: Run tests and confirm they fail**

```powershell
python -m pytest tests/ios/test_tooling.py tests/ios/test_device_provider.py -q
```

Expected: fail because iOS modules do not exist.

- [ ] **Step 4: Implement bundled tool paths**

Create `src/perfengine/ios/__init__.py` as an empty package marker.

Create `src/perfengine/ios/tooling.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from perfengine.app.errors import OperatorError


@dataclass(slots=True)
class IOSToolPaths:
    product_root: Path

    @property
    def asset_dir(self) -> Path:
        return self.product_root / "assets" / "ios"

    @property
    def go_ios_path(self) -> Path:
        return self.asset_dir / "ios.exe"

    @property
    def sib_path(self) -> Path:
        return self.asset_dir / "sib.exe"

    def require_go_ios(self) -> Path:
        if not self.go_ios_path.exists():
            raise OperatorError(
                code="ios_tool_missing",
                message="iOS tool package is incomplete. The bundled go-ios executable is missing.",
            )
        return self.go_ios_path

    def require_sib(self) -> Path:
        if not self.sib_path.exists():
            raise OperatorError(
                code="ios_tool_missing",
                message="iOS tool package is incomplete. The bundled sib executable is missing.",
            )
        return self.sib_path
```

- [ ] **Step 5: Implement iOS device discovery**

Create `src/perfengine/ios/device_provider.py`:

```python
from __future__ import annotations

import json
import subprocess

from perfengine.app.errors import OperatorError
from perfengine.app.models import DeviceInfo, Platform
from perfengine.ios.tooling import IOSToolPaths


class IOSDeviceProvider:
    def __init__(self, tool_paths: IOSToolPaths, runner=None) -> None:
        self.tool_paths = tool_paths
        self.runner = runner or subprocess.run

    def list_devices(self) -> list[DeviceInfo]:
        go_ios = self.tool_paths.require_go_ios()
        try:
            completed = self.runner(
                [go_ios, "list", "--details"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            raise OperatorError(
                code="ios_unavailable",
                message="iOS device communication is unavailable. Check the bundled iOS tools.",
            ) from exc

        if getattr(completed, "returncode", 1) != 0:
            raise OperatorError(
                code="ios_unavailable",
                message="iOS device communication is unavailable. Check USB connection and device trust.",
            )

        try:
            payload = json.loads(getattr(completed, "stdout", "") or "{}")
        except json.JSONDecodeError as exc:
            raise OperatorError(
                code="ios_unavailable",
                message="iOS device discovery returned invalid data.",
            ) from exc

        devices = []
        for item in payload.get("deviceList", []):
            udid = item.get("Udid")
            if not udid:
                continue
            product_type = item.get("ProductType") or "iPhone"
            product_version = item.get("ProductVersion") or "unknown"
            devices.append(
                DeviceInfo(
                    device_id=udid,
                    display_name=f"{product_type} (iOS {product_version})",
                    connection_type="usb",
                    platform=Platform.IOS,
                )
            )
        return devices
```

- [ ] **Step 6: Run iOS discovery tests**

```powershell
python -m pytest tests/ios/test_tooling.py tests/ios/test_device_provider.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add src/perfengine/ios tests/ios/test_tooling.py tests/ios/test_device_provider.py
git commit -m "feat: add bundled ios device discovery"
```

---

### Task 3: iOS Tunnel and App Listing

**Files:**
- Create: `src/perfengine/ios/tunnel.py`
- Create: `src/perfengine/ios/app_provider.py`
- Create: `tests/ios/test_app_provider.py`

- [ ] **Step 1: Write tunnel and app listing tests**

Create `tests/ios/test_app_provider.py`:

```python
from perfengine.app.models import Platform
from perfengine.ios.app_provider import IOSAppProvider


class FakeIOSClient:
    def __init__(self):
        self.prepared = []

    def prepare(self, device_id: str):
        self.prepared.append(device_id)

    def list_apps(self, device_id: str):
        return [
            {
                "CFBundleIdentifier": "com.demo.app",
                "CFBundleDisplayName": "Demo",
                "CFBundleShortVersionString": "1.2",
                "CFBundleVersion": "45",
            }
        ]


def test_ios_app_provider_prepares_device_and_maps_user_apps():
    client = FakeIOSClient()
    provider = IOSAppProvider(client)

    apps = provider.list_apps("ios-1")

    assert client.prepared == ["ios-1"]
    assert apps[0].package_name == "com.demo.app"
    assert apps[0].display_name == "Demo"
    assert apps[0].platform is Platform.IOS
```

- [ ] **Step 2: Run test and confirm it fails**

```powershell
python -m pytest tests/ios/test_app_provider.py -q
```

Expected: fail because `IOSAppProvider` does not exist.

- [ ] **Step 3: Implement tunnel coordinator**

Create `src/perfengine/ios/tunnel.py`:

```python
from __future__ import annotations

import subprocess
import time

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSToolPaths


class IOSTunnelManager:
    def __init__(self, tool_paths: IOSToolPaths, runner=None, sleeper=time.sleep) -> None:
        self.tool_paths = tool_paths
        self.runner = runner or subprocess.Popen
        self.sleeper = sleeper
        self.process = None

    def ensure_ready(self, product_version: str | None = None) -> None:
        if not self._requires_tunnel(product_version):
            return
        go_ios = self.tool_paths.require_go_ios()
        if self.process is None:
            try:
                self.process = self.runner(
                    [go_ios, "tunnel", "start", "--userspace"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError as exc:
                raise OperatorError(
                    code="ios_tunnel_unavailable",
                    message="iOS tunnel could not be started. Check the bundled iOS tools.",
                ) from exc
        self.sleeper(1)

    @staticmethod
    def _requires_tunnel(product_version: str | None) -> bool:
        if not product_version:
            return True
        major = product_version.split(".", 1)[0]
        return major.isdigit() and int(major) >= 17

    def stop(self) -> None:
        if self.process is not None:
            self.process.terminate()
            self.process = None
```

- [ ] **Step 4: Implement iOS app provider**

Create `src/perfengine/ios/app_provider.py`:

```python
from __future__ import annotations

from perfengine.app.models import AppInfo, Platform


class IOSAppProvider:
    def __init__(self, ios_client) -> None:
        self.ios_client = ios_client

    def list_apps(self, device_id: str) -> list[AppInfo]:
        self.ios_client.prepare(device_id)
        apps = []
        for item in self.ios_client.list_apps(device_id):
            bundle_id = item.get("CFBundleIdentifier") or item.get("bundle_id")
            if not bundle_id:
                continue
            display_name = item.get("CFBundleDisplayName") or item.get("name") or bundle_id
            apps.append(
                AppInfo(
                    package_name=bundle_id,
                    display_name=display_name,
                    platform=Platform.IOS,
                )
            )
        apps.sort(key=lambda app: app.display_name.lower())
        return apps
```

- [ ] **Step 5: Run tests**

```powershell
python -m pytest tests/ios/test_app_provider.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add src/perfengine/ios/tunnel.py src/perfengine/ios/app_provider.py tests/ios/test_app_provider.py
git commit -m "feat: add ios tunnel and app listing"
```

---

### Task 4: iOS Metric Normalization

**Files:**
- Create: `src/perfengine/ios/metrics.py`
- Create: `tests/ios/test_metrics.py`

- [ ] **Step 1: Write metric mapping tests**

Create `tests/ios/test_metrics.py`:

```python
from perfengine.app.models import PhoneStatus, Platform
from perfengine.ios.metrics import normalize_ios_metric_point


def test_normalize_ios_metric_point_maps_demo_like_fields():
    point = normalize_ios_metric_point(
        timestamp="2026-05-07T00:00:00Z",
        fps_data={"fps": 50},
        system_data={
            "cpu_data": {"SystemCPUUsage": 42.5},
            "app_data": {"cpuUsage": 12.25, "physFootprint": 268435456},
        },
        battery_data={"Temperature": None},
        status=PhoneStatus(platform=Platform.IOS, temperature_c=None),
    )

    assert point is not None
    assert point.fps == 50
    assert point.frame_time_ms == 20.0
    assert point.total_cpu_percent == 42.5
    assert point.app_cpu_percent == 12.25
    assert point.memory_mb == 256.0
    assert point.temperature_c is None


def test_normalize_ios_metric_point_returns_none_when_every_signal_missing():
    point = normalize_ios_metric_point(
        timestamp="2026-05-07T00:00:00Z",
        fps_data={},
        system_data={},
        battery_data={},
        status=PhoneStatus(platform=Platform.IOS),
    )

    assert point is None
```

- [ ] **Step 2: Run tests and confirm they fail**

```powershell
python -m pytest tests/ios/test_metrics.py -q
```

Expected: fail because `perfengine.ios.metrics` does not exist.

- [ ] **Step 3: Implement metric normalization**

Create `src/perfengine/ios/metrics.py`:

```python
from __future__ import annotations

from perfengine.app.models import MetricPoint, PhoneStatus


def normalize_ios_metric_point(
    *,
    timestamp: str,
    fps_data: dict,
    system_data: dict,
    battery_data: dict,
    status: PhoneStatus,
) -> MetricPoint | None:
    fps = _number(fps_data.get("fps") or fps_data.get("CoreAnimationFramesPerSecond"))
    frame_time_ms = round(1000 / fps, 2) if fps and fps > 0 else None

    cpu_data = system_data.get("cpu_data", {}) if system_data else {}
    app_data = system_data.get("app_data", {}) if system_data else {}

    total_cpu = _number(cpu_data.get("SystemCPUUsage"))
    app_cpu = _number(app_data.get("cpuUsage"))
    memory_bytes = _number(app_data.get("physFootprint"))
    memory_mb = round(memory_bytes / 1048576, 2) if memory_bytes is not None else None

    temperature_c = status.temperature_c
    if temperature_c is None:
        temperature_c = _number(battery_data.get("Temperature"))

    point = MetricPoint(
        timestamp=timestamp,
        fps=fps,
        frame_time_ms=frame_time_ms,
        app_cpu_percent=app_cpu,
        total_cpu_percent=total_cpu,
        memory_mb=memory_mb,
        temperature_c=temperature_c,
        battery_level=_int_or_none(battery_data.get("Capacity")),
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


def _number(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/ios/test_metrics.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add src/perfengine/ios/metrics.py tests/ios/test_metrics.py
git commit -m "feat: normalize ios metrics"
```

---

### Task 5: iOS Sampler Lifecycle

**Files:**
- Create: `src/perfengine/ios/sampler.py`
- Create: `tests/ios/test_sampler.py`

- [ ] **Step 1: Write sampler tests**

Create `tests/ios/test_sampler.py`:

```python
from perfengine.app.models import Platform
from perfengine.ios.sampler import IOSSampler


class FakeIOSClient:
    def __init__(self):
        self.started = []
        self.stopped = []

    def prepare(self, device_id: str):
        return None

    def app_is_running(self, device_id: str, bundle_id: str):
        return True

    def start_collectors(self, device_id: str, bundle_id: str):
        self.started.append((device_id, bundle_id))

    def stop_collectors(self, device_id: str):
        self.stopped.append(device_id)

    def read_status(self, device_id: str, bundle_id: str):
        return {"device_label": "iPhone", "battery_level": 80, "temperature_c": None}

    def read_fps(self, device_id: str):
        return {"fps": 50}

    def read_system(self, device_id: str, bundle_id: str):
        return {
            "cpu_data": {"SystemCPUUsage": 30},
            "app_data": {"cpuUsage": 10, "physFootprint": 104857600},
        }

    def read_battery(self, device_id: str):
        return {"Capacity": 80}


def test_ios_sampler_begin_and_read_return_status_and_point():
    client = FakeIOSClient()
    sampler = IOSSampler(client)

    sampler.begin("ios-1", "com.demo.app")
    status, point = sampler.read("ios-1", "com.demo.app")

    assert client.started == [("ios-1", "com.demo.app")]
    assert status.platform is Platform.IOS
    assert status.connection_state == "connected"
    assert status.app_state == "running"
    assert point is not None
    assert point.memory_mb == 100.0


def test_ios_sampler_returns_waiting_notice_when_point_missing():
    class EmptyClient(FakeIOSClient):
        def read_fps(self, device_id: str):
            return {}

        def read_system(self, device_id: str, bundle_id: str):
            return {}

        def read_battery(self, device_id: str):
            return {}

    sampler = IOSSampler(EmptyClient())
    sampler.begin("ios-1", "com.demo.app")
    status, point = sampler.read("ios-1", "com.demo.app")

    assert point is None
    assert status.status_notice == "Waiting for iOS data."
```

- [ ] **Step 2: Run tests and confirm they fail**

```powershell
python -m pytest tests/ios/test_sampler.py -q
```

Expected: fail because `IOSSampler` does not exist.

- [ ] **Step 3: Implement sampler**

Create `src/perfengine/ios/sampler.py`:

```python
from __future__ import annotations

from perfengine.app.errors import OperatorError
from perfengine.app.models import PhoneStatus, Platform, utc_now_iso
from perfengine.ios.metrics import normalize_ios_metric_point


class IOSSampler:
    def __init__(self, ios_client) -> None:
        self.ios_client = ios_client
        self._active_session: tuple[str, str] | None = None

    def begin(self, device_id: str, package_name: str) -> None:
        self.ios_client.prepare(device_id)
        if not self.ios_client.app_is_running(device_id, package_name):
            raise OperatorError(code="ios_app_not_running", message="The selected iOS app is not running.")
        self.ios_client.start_collectors(device_id, package_name)
        self._active_session = (device_id, package_name)

    def stop(self) -> None:
        if self._active_session is not None:
            device_id, _ = self._active_session
            self.ios_client.stop_collectors(device_id)
        self._active_session = None

    def read(self, device_id: str, package_name: str):
        if not self.ios_client.app_is_running(device_id, package_name):
            return (
                PhoneStatus(
                    platform=Platform.IOS,
                    connection_state="connected",
                    device_label=device_id,
                    app_state="exited",
                    status_notice="The target iOS app exited.",
                ),
                None,
            )

        raw_status = self.ios_client.read_status(device_id, package_name)
        status = PhoneStatus(
            platform=Platform.IOS,
            connection_state="connected",
            device_label=raw_status.get("device_label") or device_id,
            screen_state=raw_status.get("screen_state") or "unknown",
            app_state="running",
            battery_level=raw_status.get("battery_level"),
            temperature_c=raw_status.get("temperature_c"),
            last_updated_at=utc_now_iso(),
        )
        point = normalize_ios_metric_point(
            timestamp=status.last_updated_at,
            fps_data=self.ios_client.read_fps(device_id),
            system_data=self.ios_client.read_system(device_id, package_name),
            battery_data=self.ios_client.read_battery(device_id),
            status=status,
        )
        if point is None:
            status.status_notice = "Waiting for iOS data."
        elif any(
            value is None
            for value in (
                point.fps,
                point.frame_time_ms,
                point.app_cpu_percent,
                point.total_cpu_percent,
                point.memory_mb,
                point.temperature_c,
            )
        ):
            status.status_notice = "Some iOS metrics are unavailable."
        return status, point
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/ios/test_sampler.py tests/ios/test_metrics.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add src/perfengine/ios/sampler.py tests/ios/test_sampler.py
git commit -m "feat: add ios sampler lifecycle"
```

---

### Task 6: Application Wiring

**Files:**
- Modify: `src/perfengine/main.py`
- Create: `src/perfengine/ios/client.py`
- Test: `tests/app/test_platform_dispatch.py`, `tests/ios/*.py`

- [ ] **Step 1: Add an iOS client facade**

Create `src/perfengine/ios/client.py` with adapter method names used by previous tasks. Keep it thin and allow dependency injection for tests:

```python
from __future__ import annotations

from pathlib import Path

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSToolPaths
from perfengine.ios.tunnel import IOSTunnelManager


class IOSClient:
    def __init__(self, product_root: Path, backend=None) -> None:
        self.tool_paths = IOSToolPaths(product_root=product_root)
        self.tunnel = IOSTunnelManager(self.tool_paths)
        self.backend = backend

    def prepare(self, device_id: str) -> None:
        self.tool_paths.require_go_ios()
        self.tunnel.ensure_ready()
        if self.backend is None:
            raise OperatorError(
                code="ios_backend_missing",
                message="iOS performance services are unavailable in this build.",
            )

    def list_apps(self, device_id: str):
        return self.backend.list_apps(device_id)

    def app_is_running(self, device_id: str, bundle_id: str) -> bool:
        return self.backend.app_is_running(device_id, bundle_id)

    def start_collectors(self, device_id: str, bundle_id: str) -> None:
        self.backend.start_collectors(device_id, bundle_id)

    def stop_collectors(self, device_id: str) -> None:
        self.backend.stop_collectors(device_id)

    def read_status(self, device_id: str, bundle_id: str) -> dict:
        return self.backend.read_status(device_id, bundle_id)

    def read_fps(self, device_id: str) -> dict:
        return self.backend.read_fps(device_id)

    def read_system(self, device_id: str, bundle_id: str) -> dict:
        return self.backend.read_system(device_id, bundle_id)

    def read_battery(self, device_id: str) -> dict:
        return self.backend.read_battery(device_id)
```

- [ ] **Step 2: Wire registry in `main.py`**

Replace direct Android-only service construction with:

```python
from pathlib import Path

from perfengine.app.models import Platform
from perfengine.app.platforms import PlatformRegistry
from perfengine.ios.app_provider import IOSAppProvider
from perfengine.ios.client import IOSClient
from perfengine.ios.device_provider import IOSDeviceProvider
from perfengine.ios.sampler import IOSSampler
from perfengine.ios.tooling import IOSToolPaths


def build_application() -> BridgeApi:
    product_root = Path(__file__).resolve().parents[2]

    adb_client = AdbClient()
    android_device_provider = DeviceProvider(adb_client)
    android_app_provider = AppProvider(adb_client)
    android_status_provider = StatusProvider(adb_client)
    android_collector = AndroidSampler(adb_client, android_status_provider)

    ios_client = IOSClient(product_root=product_root)
    ios_tool_paths = IOSToolPaths(product_root=product_root)

    registry = PlatformRegistry()
    registry.register(
        Platform.ANDROID,
        provider=_CombinedProvider(android_device_provider, android_app_provider),
        collector=android_collector,
    )
    registry.register(
        Platform.IOS,
        provider=_CombinedProvider(
            IOSDeviceProvider(ios_tool_paths),
            IOSAppProvider(ios_client),
        ),
        collector=IOSSampler(ios_client),
    )
    service = PerfToolService(platform_registry=registry)
    return BridgeApi(service)
```

Add the local helper class:

```python
class _CombinedProvider:
    def __init__(self, device_provider, app_provider) -> None:
        self.device_provider = device_provider
        self.app_provider = app_provider

    def list_devices(self):
        return self.device_provider.list_devices()

    def list_apps(self, device_id: str):
        return self.app_provider.list_apps(device_id)
```

- [ ] **Step 3: Run backend tests**

```powershell
python -m pytest tests/app tests/android tests/ios -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```powershell
git add src/perfengine/main.py src/perfengine/ios/client.py
git commit -m "feat: wire ios platform backend"
```

---

### Task 7: UI Platform Fields and Status Prompts

**Files:**
- Modify: `ui/src/types.ts`
- Modify: `ui/src/state/sessionStore.ts`
- Modify: `ui/src/components/ToolbarPanel.vue`
- Modify: `ui/src/components/StatusCard.vue`
- Test: `ui/src/state/sessionStore.spec.ts`
- Test: `ui/src/components/ToolbarPanel.spec.ts`

- [ ] **Step 1: Update UI types**

In `ui/src/types.ts`, add:

```ts
export type Platform = 'android' | 'ios'
```

Then add fields:

```ts
platform: Platform
```

to `DeviceInfo` and `AppInfo`, and:

```ts
platform: Platform | null
```

to `SessionState` and `PhoneStatus`. Add:

```ts
status_notice: string
```

to `PhoneStatus`.

- [ ] **Step 2: Write store test for status prompts**

Add to `ui/src/state/sessionStore.spec.ts`:

```ts
it('keeps iOS partial metric status visible while running', async () => {
  const api = createFakeApi({
    snapshot: {
      session: {
        phase: 'running',
        selected_device_id: 'ios-1',
        selected_package: 'com.demo.app',
        selectors_locked: true,
        message: '',
        platform: 'ios',
      },
      status: {
        platform: 'ios',
        connection_state: 'connected',
        device_label: 'iPhone',
        screen_state: 'unknown',
        app_state: 'running',
        battery_level: null,
        temperature_c: null,
        status_notice: 'Some iOS metrics are unavailable.',
        last_updated_at: '2026-05-07T00:00:00Z',
      },
      metrics: [],
    },
  })
  const store = createSessionStore(api)

  await store.pollOnce()

  expect(store.errorMessage).toBe('Some iOS metrics are unavailable.')
})
```

If `createFakeApi` does not exist, add a local helper in the spec:

```ts
function createFakeApi(overrides: Partial<SessionApi> & { snapshot?: LiveSnapshot }): SessionApi {
  return {
    listDevices: async () => [],
    listApps: async () => [],
    startSession: async () => ({
      phase: 'running',
      selected_device_id: 'ios-1',
      selected_package: 'com.demo.app',
      selectors_locked: true,
      message: '',
      platform: 'ios',
    }),
    stopSession: async () => ({
      phase: 'stopped',
      selected_device_id: 'ios-1',
      selected_package: 'com.demo.app',
      selectors_locked: false,
      message: '',
      platform: 'ios',
    }),
    getLiveSnapshot: async () => overrides.snapshot as LiveSnapshot,
    ...overrides,
  }
}
```

- [ ] **Step 3: Run UI test and confirm it fails**

```powershell
npm.cmd test -- sessionStore.spec.ts --run
```

Expected: fail because types/status handling are not updated.

- [ ] **Step 4: Implement status handling**

In `ui/src/state/sessionStore.ts`, after assigning `state.snapshot`, compute:

```ts
const statusNotice = state.snapshot.status?.status_notice ?? ''
if (statusNotice) {
  state.errorMessage = statusNotice
} else if (state.session.phase === 'interrupted' || state.session.phase === 'error') {
  state.errorMessage = state.session.message
  stopPolling()
  return
} else if (state.session.phase === 'running') {
  state.errorMessage = ''
}
```

- [ ] **Step 5: Show platform in toolbar**

In `ToolbarPanel.vue`, render device options as:

```vue
{{ device.display_name }} [{{ device.platform }}] ({{ device.device_id }})
```

- [ ] **Step 6: Show status notice in status card**

In `StatusCard.vue`, compute message priority in template:

```vue
{{ errorMessage || status?.status_notice || session.message || session.phase }}
```

For unknown values, keep explicit `unknown` or `Unavailable`, not zero.

- [ ] **Step 7: Run UI tests**

```powershell
npm.cmd test -- --run
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add ui/src/types.ts ui/src/state/sessionStore.ts ui/src/components/ToolbarPanel.vue ui/src/components/StatusCard.vue ui/src/state/sessionStore.spec.ts ui/src/components/ToolbarPanel.spec.ts
git commit -m "feat: show ios platform status in ui"
```

---

### Task 8: Manual Verification Checklist

**Files:**
- Create: `docs/manual-tests/ios-mvp-support.md`
- Modify: `openspec/changes/add-ios-mvp-support/tasks.md`

- [ ] **Step 1: Create manual checklist**

Create `docs/manual-tests/ios-mvp-support.md`:

```markdown
# iOS MVP Support Manual Verification

## Environment

- Windows host
- PerfEngine package with bundled iOS tools
- Trusted iPhone connected over USB
- iPhone Developer Mode enabled when required
- Target iOS app installed

## Checklist

- [ ] Launch PerfEngine without relying on user-installed go-ios, sib, or pymobiledevice CLI tools.
- [ ] Refresh devices.
- [ ] Confirm the iPhone appears with platform `ios`.
- [ ] Select the iPhone.
- [ ] Confirm user apps load.
- [ ] Select target app.
- [ ] Start collection.
- [ ] Confirm selectors are locked and Stop is visible.
- [ ] Confirm the status card shows iOS device identity and app state.
- [ ] Confirm FPS, Frame Time, App CPU, Total CPU, Memory, and Temperature charts either show data or a visible status prompt for missing values.
- [ ] Exit the target app during collection.
- [ ] Confirm the session enters interrupted/error state with an operator-readable message.
- [ ] Reconnect or reselect the iPhone and confirm retry does not require restarting the tool.
- [ ] Stop collection.
- [ ] Confirm selectors unlock and final visible results remain on screen.

## Metric Observations

Record observed behavior:

- FPS:
- Frame Time:
- App CPU:
- Total CPU:
- Memory:
- Temperature:
- Missing or unknown fields:
- iOS version:
- Device model:
```

- [ ] **Step 2: Update OpenSpec task completion guidance**

In `openspec/changes/add-ios-mvp-support/tasks.md`, leave task checkboxes unchecked until implementation. Add a note under verification:

```markdown
Manual verification is user-run. The implementer prepares the checklist and records results supplied by the user before marking manual verification tasks complete.
```

- [ ] **Step 3: Commit**

```powershell
git add docs/manual-tests/ios-mvp-support.md openspec/changes/add-ios-mvp-support/tasks.md
git commit -m "docs: add ios manual verification checklist"
```

---

### Task 9: Final Verification and OpenSpec Readiness

**Files:**
- Modify only if test failures require fixes in files touched by prior tasks.

- [ ] **Step 1: Run backend tests**

```powershell
python -m pytest tests -q
```

Expected: all Python tests pass.

- [ ] **Step 2: Run UI tests**

```powershell
npm.cmd test -- --run
```

Expected: all UI tests pass.

- [ ] **Step 3: Build UI**

```powershell
npm.cmd run build
```

Expected: Vite build succeeds and writes `ui/dist`.

- [ ] **Step 4: Run OpenSpec status**

```powershell
openspec.cmd status --change add-ios-mvp-support
```

Expected:

```text
Progress: 4/4 artifacts complete
All artifacts complete!
```

- [ ] **Step 5: Commit final verification fixes if any**

If no files changed, do not create an empty commit. If fixes were needed:

```powershell
git add <changed-files>
git commit -m "test: verify ios mvp support"
```

---

## Self-Review

Spec coverage:
- `ios-session-control`: Tasks 1, 2, 3, 5, 6, 8 cover device discovery, app listing, single-session lifecycle, startup failure, tunnel readiness, and operator messages.
- `ios-live-visibility`: Tasks 4, 5, 7, 8 cover Android-aligned charts, missing metrics, status card, interruptions, and manual verification.

No placeholders:
- All tasks include exact files, commands, and expected outcomes.
- Open implementation uncertainty is isolated behind `IOSClient` and verified with fake clients before real backend integration.

Type consistency:
- Backend uses `Platform.ANDROID` and `Platform.IOS`.
- Frontend uses `'android' | 'ios'`.
- `status_notice` is added to `PhoneStatus` in both Python and TypeScript.
