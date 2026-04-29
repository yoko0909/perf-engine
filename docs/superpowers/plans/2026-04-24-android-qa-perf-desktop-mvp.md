# Android QA 桌面性能 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Android-only 的 QA 桌面性能工具 MVP，让测试同学可以在单页界面中刷新设备、选择应用、开始或停止采集，并实时看到固定图表和手机状态。

**Architecture:** 后端使用 Python 的三层结构：`android` 负责 ADB 和指标采样，`app` 负责单会话状态机与统一快照，`ui` 负责 pywebview 桥接。前端使用 Vue 3 + Vite 构建单页仪表盘，每秒轮询一次 `get_live_snapshot()`，只消费统一的 UI 模型，不直接碰采集细节。

**Tech Stack:** Python 3.11、pytest、pywebview、Vue 3、Vite、Vitest、ECharts、ADB

---

## 文件结构

### 后端文件

- Create: `pyproject.toml`
  Python 工程配置，声明 `pywebview` 和 `pytest` 依赖。
- Create: `src/perfengine/__init__.py`
  标记 `perfengine` 包。
- Create: `src/perfengine/app/models.py`
  统一定义 `DeviceInfo`、`AppInfo`、`SessionState`、`PhoneStatus`、`MetricPoint`、`LiveSnapshot`。
- Create: `src/perfengine/app/__init__.py`
  标记 `app` 子包。
- Create: `src/perfengine/app/errors.py`
  定义运营可读错误 `OperatorError`。
- Create: `src/perfengine/app/service.py`
  单会话服务层，对外暴露 `list_devices`、`list_apps`、`start_session`、`stop_session`、`get_live_snapshot`。
- Create: `src/perfengine/android/adb_client.py`
  统一执行 ADB 命令并屏蔽 subprocess 细节。
- Create: `src/perfengine/android/__init__.py`
  标记 `android` 子包。
- Create: `src/perfengine/android/device_provider.py`
  负责解析 `adb devices -l`。
- Create: `src/perfengine/android/app_provider.py`
  负责获取 Android 设备应用列表。
- Create: `src/perfengine/android/status_provider.py`
  负责获取连接状态、屏幕状态、目标应用状态、电量、温度。
- Create: `src/perfengine/android/metrics.py`
  解析 CPU、内存、FPS、Frame Time 文本输出。
- Create: `src/perfengine/android/sampler.py`
  基于 ADB 和 provider 拼装单次采样结果。
- Create: `src/perfengine/ui/bridge.py`
  pywebview 对外桥接层，把 dataclass 转成 JSON-ready 字典。
- Create: `src/perfengine/ui/__init__.py`
  标记 `ui` 子包。
- Create: `src/perfengine/ui/window.py`
  定位前端入口并创建桌面窗口。
- Create: `src/perfengine/main.py`
  桌面程序入口。

### 前端文件

- Create: `ui/package.json`
  前端依赖和脚本。
- Create: `ui/tsconfig.json`
  TypeScript 配置。
- Create: `ui/vite.config.ts`
  Vite 与 Vitest 配置。
- Create: `ui/index.html`
  前端挂载入口。
- Create: `ui/src/main.ts`
  启动 Vue 应用。
- Create: `ui/src/types.ts`
  与后端对齐的前端类型。
- Create: `ui/src/api.ts`
  调用 `window.pywebview.api` 的 API 封装。
- Create: `ui/src/state/sessionStore.ts`
  前端状态与轮询逻辑。
- Create: `ui/src/App.vue`
  单页主视图。
- Create: `ui/src/components/ToolbarPanel.vue`
  顶部操作区。
- Create: `ui/src/components/StatusCard.vue`
  手机与会话状态卡。
- Create: `ui/src/components/MetricChart.vue`
  单个图表组件。

### 测试与文档

- Create: `tests/app/test_models.py`
- Create: `tests/app/test_service.py`
- Create: `tests/app/test_error_states.py`
- Create: `tests/android/test_providers.py`
- Create: `tests/android/test_sampler.py`
- Create: `tests/ui/test_bridge.py`
- Create: `ui/src/state/sessionStore.spec.ts`
- Create: `ui/src/components/ToolbarPanel.spec.ts`
- Create: `docs/manual-tests/android-qa-perf-desktop-mvp.md`

### 只读参考

- Read: `Perftool_Demo/main.py`
- Read: `Perftool_Demo/android/android_perf_client.py`
- Read: `Perftool_Demo/ToolUI/src/App.vue`

这些文件只用于参考产品形态和已有采集思路，不要在实现过程中直接复制整块代码。

### Task 1: Python 工程骨架与共享模型

**Files:**
- Create: `pyproject.toml`
- Create: `src/perfengine/__init__.py`
- Create: `src/perfengine/app/__init__.py`
- Create: `src/perfengine/app/models.py`
- Create: `src/perfengine/app/errors.py`
- Test: `tests/app/test_models.py`

- [ ] **Step 1: 写第一个失败测试和 Python 工程配置**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "perfengine"
version = "0.1.0"
description = "Android QA desktop performance MVP"
requires-python = ">=3.11"
dependencies = [
  "pywebview>=5.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0"
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# tests/app/test_models.py
from perfengine.app.errors import OperatorError
from perfengine.app.models import (
    LiveSnapshot,
    PhoneStatus,
    SessionPhase,
    SessionState,
)


def test_live_snapshot_uses_domain_defaults():
    state = SessionState(
        phase=SessionPhase.IDLE,
        selected_device_id=None,
        selected_package=None,
        selectors_locked=False,
        message="",
    )
    status = PhoneStatus(
        connection_state="disconnected",
        device_label="",
        screen_state="unknown",
        app_state="not_selected",
        battery_level=None,
        temperature_c=None,
        last_updated_at="2026-04-24T00:00:00Z",
    )

    snapshot = LiveSnapshot(session=state, status=status, metrics=[])

    assert snapshot.metrics == []
    assert snapshot.session.phase is SessionPhase.IDLE


def test_operator_error_keeps_user_facing_message():
    error = OperatorError(code="adb_unavailable", message="Android 设备通信不可用")

    assert error.code == "adb_unavailable"
    assert error.message == "Android 设备通信不可用"
```

- [ ] **Step 2: 安装 Python 开发依赖**

Run: `python -m pip install -e .[dev]`  
Expected: 输出包含 `Successfully installed`，并且当前仓库可直接执行 `python -m pytest`

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/app/test_models.py -q`  
Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'perfengine.app'`

- [ ] **Step 4: 编写最小实现**

```python
# src/perfengine/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/perfengine/app/__init__.py
__all__ = ["models", "errors"]
```

```python
# src/perfengine/app/errors.py
from dataclasses import dataclass


@dataclass(slots=True)
class OperatorError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message
```

```python
# src/perfengine/app/models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
    connection_type: str


@dataclass(slots=True)
class AppInfo:
    package_name: str
    display_name: str


@dataclass(slots=True)
class SessionState:
    phase: SessionPhase
    selected_device_id: str | None
    selected_package: str | None
    selectors_locked: bool
    message: str


@dataclass(slots=True)
class PhoneStatus:
    connection_state: str
    device_label: str
    screen_state: str
    app_state: str
    battery_level: int | None
    temperature_c: float | None
    last_updated_at: str


@dataclass(slots=True)
class MetricPoint:
    timestamp: str
    fps: float | None
    frame_time_ms: float | None
    app_cpu_percent: float | None
    total_cpu_percent: float | None
    memory_mb: float | None
    temperature_c: float | None
    battery_level: int | None


@dataclass(slots=True)
class LiveSnapshot:
    session: SessionState
    status: PhoneStatus
    metrics: list[MetricPoint]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python -m pytest tests/app/test_models.py -q`  
Expected: PASS，输出为 `2 passed`

- [ ] **Step 6: 提交**

```bash
git add pyproject.toml src/perfengine/__init__.py src/perfengine/app/__init__.py src/perfengine/app/models.py src/perfengine/app/errors.py tests/app/test_models.py
git commit -m "chore: bootstrap python package and domain models"
```

### Task 2: 服务层状态机

**Files:**
- Create: `src/perfengine/app/service.py`
- Test: `tests/app/test_service.py`
- Modify: `src/perfengine/app/models.py`

- [ ] **Step 1: 写服务层失败测试**

```python
# tests/app/test_service.py
from perfengine.app.models import AppInfo, DeviceInfo, SessionPhase
from perfengine.app.service import PerfToolService


class FakeDeviceProvider:
    def list_devices(self):
        return [DeviceInfo(device_id="SERIAL1", display_name="Pixel 8", connection_type="usb")]


class FakeAppProvider:
    def list_apps(self, device_id: str):
        assert device_id == "SERIAL1"
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]


class FakeCollector:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def begin(self, device_id: str, package_name: str):
        if self.should_fail:
            raise RuntimeError("collector failed")

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        raise NotImplementedError


def test_start_session_locks_selectors():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=FakeCollector(),
    )

    service.list_devices()
    service.list_apps("SERIAL1")
    state = service.start_session("SERIAL1", "com.demo.app")

    assert state.phase is SessionPhase.RUNNING
    assert state.selectors_locked is True


def test_start_session_failure_returns_error_state():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=FakeCollector(should_fail=True),
    )

    state = service.start_session("SERIAL1", "com.demo.app")

    assert state.phase is SessionPhase.ERROR
    assert state.selectors_locked is False
    assert state.message == "采集启动失败，请重试"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/app/test_service.py -q`  
Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'perfengine.app.service'`

- [ ] **Step 3: 编写最小实现**

```python
# src/perfengine/app/service.py
from __future__ import annotations

from datetime import datetime, timezone

from perfengine.app.models import LiveSnapshot, PhoneStatus, SessionPhase, SessionState


class PerfToolService:
    def __init__(self, device_provider, app_provider, collector):
        self.device_provider = device_provider
        self.app_provider = app_provider
        self.collector = collector
        self.history = []
        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=None,
            selected_package=None,
            selectors_locked=False,
            message="",
        )
        self.status = PhoneStatus(
            connection_state="disconnected",
            device_label="",
            screen_state="unknown",
            app_state="not_selected",
            battery_level=None,
            temperature_c=None,
            last_updated_at=self._now(),
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_devices(self):
        self.state.phase = SessionPhase.LOADING_DEVICES
        devices = self.device_provider.list_devices()
        self.state.phase = SessionPhase.IDLE
        return devices

    def list_apps(self, device_id: str):
        self.state.phase = SessionPhase.LOADING_APPS
        apps = self.app_provider.list_apps(device_id)
        self.state.phase = SessionPhase.IDLE
        self.state.selected_device_id = device_id
        return apps

    def start_session(self, device_id: str, package_name: str) -> SessionState:
        self.state = SessionState(
            phase=SessionPhase.STARTING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="正在启动采集",
        )
        try:
            self.collector.begin(device_id, package_name)
        except Exception:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message="采集启动失败，请重试",
            )
            return self.state

        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="采集中",
        )
        return self.state

    def stop_session(self) -> SessionState:
        self.collector.stop()
        self.state = SessionState(
            phase=SessionPhase.STOPPED,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="已停止",
        )
        return self.state

    def get_live_snapshot(self) -> LiveSnapshot:
        return LiveSnapshot(session=self.state, status=self.status, metrics=self.history)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/app/test_service.py -q`  
Expected: PASS，输出为 `2 passed`

- [ ] **Step 5: 提交**

```bash
git add src/perfengine/app/service.py src/perfengine/app/models.py tests/app/test_service.py
git commit -m "feat: add service layer session state machine"
```

### Task 3: ADB 访问层与 Android Provider

**Files:**
- Create: `src/perfengine/android/adb_client.py`
- Create: `src/perfengine/android/device_provider.py`
- Create: `src/perfengine/android/app_provider.py`
- Create: `src/perfengine/android/status_provider.py`
- Test: `tests/android/test_providers.py`

- [ ] **Step 1: 写 Provider 失败测试**

```python
# tests/android/test_providers.py
from perfengine.android.adb_client import AdbClient
from perfengine.android.app_provider import AppProvider
from perfengine.android.device_provider import DeviceProvider
from perfengine.android.status_provider import StatusProvider


class FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def fake_runner_factory(outputs):
    def _runner(cmd):
        key = " ".join(cmd)
        return FakeCompletedProcess(stdout=outputs[key])
    return _runner


def test_device_provider_parses_adb_devices_output():
    outputs = {
        "adb devices -l": "List of devices attached\nSERIAL1 device product:husky model:Pixel_8 device:husky transport_id:1\n"
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = DeviceProvider(client)

    devices = provider.list_devices()

    assert devices[0].device_id == "SERIAL1"
    assert devices[0].display_name == "Pixel_8"


def test_status_provider_uses_unknown_when_screen_state_is_missing():
    outputs = {
        "adb -s SERIAL1 shell dumpsys battery": "level: 87\ntemperature: 320\n",
        "adb -s SERIAL1 shell dumpsys power": "Display Power: state=\n",
        "adb -s SERIAL1 shell pidof com.demo.app": "2314\n",
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = StatusProvider(client)

    status = provider.get_phone_status("SERIAL1", "com.demo.app")

    assert status.battery_level == 87
    assert status.temperature_c == 32.0
    assert status.screen_state == "unknown"
    assert status.app_state == "running"


def test_app_provider_returns_package_names_as_labels():
    outputs = {
        "adb -s SERIAL1 shell pm list packages -3": "package:com.demo.app\npackage:com.android.settings\n"
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    provider = AppProvider(client)

    apps = provider.list_apps("SERIAL1")

    assert apps[0].package_name == "com.demo.app"
    assert apps[0].display_name == "com.demo.app"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/android/test_providers.py -q`  
Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'perfengine.android'`

- [ ] **Step 3: 编写最小实现**

```python
# src/perfengine/android/adb_client.py
from __future__ import annotations

import subprocess

from perfengine.app.errors import OperatorError


class AdbClient:
    def __init__(self, adb_path: str = "adb", runner=None):
        self.adb_path = adb_path
        self.runner = runner or self._default_runner

    def _default_runner(self, cmd: list[str]):
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def run(self, args: list[str], serial: str | None = None) -> str:
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        completed = self.runner(cmd)
        if completed.returncode != 0:
            raise OperatorError(code="adb_unavailable", message="Android 设备通信不可用")
        return completed.stdout
```

```python
# src/perfengine/android/__init__.py
__all__ = ["adb_client", "app_provider", "device_provider", "status_provider"]
```

```python
# src/perfengine/android/device_provider.py
from perfengine.app.models import DeviceInfo


class DeviceProvider:
    def __init__(self, adb_client):
        self.adb_client = adb_client

    def list_devices(self) -> list[DeviceInfo]:
        output = self.adb_client.run(["devices", "-l"])
        devices: list[DeviceInfo] = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2 or parts[1] != "device":
                continue
            device_id = parts[0]
            model = next((part.split(":", 1)[1] for part in parts if part.startswith("model:")), device_id)
            devices.append(DeviceInfo(device_id=device_id, display_name=model, connection_type="usb"))
        return devices
```

```python
# src/perfengine/android/app_provider.py
from perfengine.app.models import AppInfo


class AppProvider:
    def __init__(self, adb_client):
        self.adb_client = adb_client

    def list_apps(self, device_id: str) -> list[AppInfo]:
        output = self.adb_client.run(["shell", "pm", "list", "packages", "-3"], serial=device_id)
        apps: list[AppInfo] = []
        for line in output.splitlines():
            if not line.startswith("package:"):
                continue
            package_name = line.split(":", 1)[1].strip()
            apps.append(AppInfo(package_name=package_name, display_name=package_name))
        return apps
```

```python
# src/perfengine/android/status_provider.py
from __future__ import annotations

from datetime import datetime, timezone

from perfengine.app.models import PhoneStatus


class StatusProvider:
    def __init__(self, adb_client):
        self.adb_client = adb_client

    def _parse_battery(self, raw: str) -> tuple[int | None, float | None]:
        level = None
        temperature_c = None
        for line in raw.splitlines():
            if line.strip().startswith("level:"):
                level = int(line.split(":", 1)[1].strip())
            if line.strip().startswith("temperature:"):
                temperature_c = int(line.split(":", 1)[1].strip()) / 10
        return level, temperature_c

    def _parse_screen_state(self, raw: str) -> str:
        if "state=ON" in raw:
            return "on"
        if "state=OFF" in raw:
            return "off"
        return "unknown"

    def get_phone_status(self, device_id: str, package_name: str) -> PhoneStatus:
        battery_raw = self.adb_client.run(["shell", "dumpsys", "battery"], serial=device_id)
        power_raw = self.adb_client.run(["shell", "dumpsys", "power"], serial=device_id)
        pid_raw = self.adb_client.run(["shell", "pidof", package_name], serial=device_id)

        battery_level, temperature_c = self._parse_battery(battery_raw)
        screen_state = self._parse_screen_state(power_raw)
        app_state = "running" if pid_raw.strip() else "not_running"

        return PhoneStatus(
            connection_state="connected",
            device_label=device_id,
            screen_state=screen_state,
            app_state=app_state,
            battery_level=battery_level,
            temperature_c=temperature_c,
            last_updated_at=datetime.now(timezone.utc).isoformat(),
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/android/test_providers.py -q`  
Expected: PASS，输出为 `3 passed`

- [ ] **Step 5: 提交**

```bash
git add src/perfengine/android/__init__.py src/perfengine/android/adb_client.py src/perfengine/android/device_provider.py src/perfengine/android/app_provider.py src/perfengine/android/status_provider.py tests/android/test_providers.py
git commit -m "feat: add android adb providers"
```

### Task 4: 采样器与统一快照

**Files:**
- Create: `src/perfengine/android/metrics.py`
- Create: `src/perfengine/android/sampler.py`
- Test: `tests/android/test_sampler.py`
- Modify: `src/perfengine/app/service.py`

- [ ] **Step 1: 写采样器失败测试**

```python
# tests/android/test_sampler.py
from perfengine.android.metrics import parse_metric_outputs
from perfengine.android.sampler import AndroidSampler
from perfengine.app.models import SessionPhase
from perfengine.app.service import PerfToolService


class FakeStatusProvider:
    def get_phone_status(self, device_id: str, package_name: str):
        from perfengine.app.models import PhoneStatus
        return PhoneStatus(
            connection_state="connected",
            device_label=device_id,
            screen_state="on",
            app_state="running",
            battery_level=88,
            temperature_c=33.5,
            last_updated_at="2026-04-24T00:00:00Z",
        )


class FakeAdbClient:
    def run(self, args, serial=None):
        cmd = " ".join(args)
        if "top -b -n 1" in cmd:
            return "1234 u0_a123 12% S 256M com.demo.app\n"
        if "dumpsys cpuinfo" in cmd:
            return "TOTAL: 37% user + 14% kernel\n"
        if "dumpsys meminfo" in cmd:
            return "TOTAL PSS: 262144\n"
        if "dumpsys gfxinfo" in cmd:
            return "50th percentile: 16ms\n90th percentile: 24ms\n"
        return ""


def test_parse_metric_outputs_returns_expected_numbers():
    point = parse_metric_outputs(
        cpu_raw="1234 u0_a123 12% S 256M com.demo.app\n",
        total_cpu_raw="TOTAL: 37% user + 14% kernel\n",
        mem_raw="TOTAL PSS: 262144\n",
        gfx_raw="50th percentile: 16ms\n90th percentile: 24ms\n",
        battery_level=88,
        temperature_c=33.5,
        timestamp="2026-04-24T00:00:00Z",
    )

    assert point.app_cpu_percent == 12.0
    assert point.total_cpu_percent == 37.0
    assert point.memory_mb == 256.0
    assert point.frame_time_ms == 16.0
    assert point.fps == 62.5


def test_service_get_live_snapshot_appends_metric_history():
    sampler = AndroidSampler(adb_client=FakeAdbClient(), status_provider=FakeStatusProvider())
    service = PerfToolService(device_provider=None, app_provider=None, collector=sampler)

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.RUNNING
    assert len(snapshot.metrics) == 1
    assert snapshot.status.battery_level == 88
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/android/test_sampler.py -q`  
Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'perfengine.android.metrics'`

- [ ] **Step 3: 编写最小实现**

```python
# src/perfengine/android/metrics.py
from __future__ import annotations

import re

from perfengine.app.models import MetricPoint


def _extract_first_float(pattern: str, raw: str) -> float | None:
    match = re.search(pattern, raw)
    if not match:
        return None
    return float(match.group(1))


def parse_metric_outputs(
    cpu_raw: str,
    total_cpu_raw: str,
    mem_raw: str,
    gfx_raw: str,
    battery_level: int | None,
    temperature_c: float | None,
    timestamp: str,
) -> MetricPoint:
    app_cpu = _extract_first_float(r"(\d+(?:\.\d+)?)%", cpu_raw)
    total_cpu = _extract_first_float(r"TOTAL:\s+(\d+(?:\.\d+)?)%", total_cpu_raw)
    total_pss_kb = _extract_first_float(r"TOTAL PSS:\s+(\d+(?:\.\d+)?)", mem_raw)
    frame_time = _extract_first_float(r"50th percentile:\s+(\d+(?:\.\d+)?)ms", gfx_raw)
    fps = round(1000 / frame_time, 2) if frame_time else None

    return MetricPoint(
        timestamp=timestamp,
        fps=fps,
        frame_time_ms=frame_time,
        app_cpu_percent=app_cpu,
        total_cpu_percent=total_cpu,
        memory_mb=round(total_pss_kb / 1024, 2) if total_pss_kb else None,
        temperature_c=temperature_c,
        battery_level=battery_level,
    )
```

```python
# src/perfengine/android/sampler.py
from __future__ import annotations

from datetime import datetime, timezone

from perfengine.android.metrics import parse_metric_outputs


class AndroidSampler:
    def __init__(self, adb_client, status_provider):
        self.adb_client = adb_client
        self.status_provider = status_provider
        self.active_device_id = None
        self.active_package = None

    def begin(self, device_id: str, package_name: str):
        self.active_device_id = device_id
        self.active_package = package_name

    def stop(self):
        self.active_device_id = None
        self.active_package = None

    def read(self, device_id: str, package_name: str):
        status = self.status_provider.get_phone_status(device_id, package_name)
        timestamp = datetime.now(timezone.utc).isoformat()
        cpu_raw = self.adb_client.run(["shell", f"top -b -n 1 | grep {package_name}"], serial=device_id)
        total_cpu_raw = self.adb_client.run(["shell", "dumpsys", "cpuinfo"], serial=device_id)
        mem_raw = self.adb_client.run(["shell", "dumpsys", "meminfo", package_name], serial=device_id)
        gfx_raw = self.adb_client.run(["shell", "dumpsys", "gfxinfo", package_name], serial=device_id)
        point = parse_metric_outputs(
            cpu_raw=cpu_raw,
            total_cpu_raw=total_cpu_raw,
            mem_raw=mem_raw,
            gfx_raw=gfx_raw,
            battery_level=status.battery_level,
            temperature_c=status.temperature_c,
            timestamp=timestamp,
        )
        return status, point
```

```python
# src/perfengine/app/service.py
from __future__ import annotations

from datetime import datetime, timezone

from perfengine.app.models import LiveSnapshot, PhoneStatus, SessionPhase, SessionState


class PerfToolService:
    def __init__(self, device_provider, app_provider, collector):
        self.device_provider = device_provider
        self.app_provider = app_provider
        self.collector = collector
        self.history = []
        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=None,
            selected_package=None,
            selectors_locked=False,
            message="",
        )
        self.status = PhoneStatus(
            connection_state="disconnected",
            device_label="",
            screen_state="unknown",
            app_state="not_selected",
            battery_level=None,
            temperature_c=None,
            last_updated_at=self._now(),
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_devices(self):
        if self.device_provider is None:
            return []
        self.state.phase = SessionPhase.LOADING_DEVICES
        devices = self.device_provider.list_devices()
        self.state.phase = SessionPhase.IDLE
        return devices

    def list_apps(self, device_id: str):
        if self.app_provider is None:
            return []
        self.state.phase = SessionPhase.LOADING_APPS
        apps = self.app_provider.list_apps(device_id)
        self.state.phase = SessionPhase.IDLE
        self.state.selected_device_id = device_id
        return apps

    def start_session(self, device_id: str, package_name: str) -> SessionState:
        self.state = SessionState(
            phase=SessionPhase.STARTING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="正在启动采集",
        )
        try:
            self.collector.begin(device_id, package_name)
        except Exception:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message="采集启动失败，请重试",
            )
            return self.state

        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="采集中",
        )
        return self.state

    def stop_session(self) -> SessionState:
        self.collector.stop()
        self.state = SessionState(
            phase=SessionPhase.STOPPED,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="已停止",
        )
        return self.state

    def get_live_snapshot(self) -> LiveSnapshot:
        if self.state.phase is SessionPhase.RUNNING:
            status, point = self.collector.read(self.state.selected_device_id, self.state.selected_package)
            self.status = status
            self.history.append(point)
            self.history = self.history[-60:]
        return LiveSnapshot(session=self.state, status=self.status, metrics=self.history)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/android/test_sampler.py -q`  
Expected: PASS，输出为 `2 passed`

- [ ] **Step 5: 提交**

```bash
git add src/perfengine/android/metrics.py src/perfengine/android/sampler.py src/perfengine/app/service.py tests/android/test_sampler.py
git commit -m "feat: add live metric sampler and snapshot history"
```

### Task 5: pywebview 桥接与桌面入口

**Files:**
- Create: `src/perfengine/ui/__init__.py`
- Create: `src/perfengine/ui/bridge.py`
- Create: `src/perfengine/ui/window.py`
- Create: `src/perfengine/main.py`
- Test: `tests/ui/test_bridge.py`

- [ ] **Step 1: 写桥接层失败测试**

```python
# tests/ui/test_bridge.py
from perfengine.app.models import LiveSnapshot, PhoneStatus, SessionPhase, SessionState
from perfengine.ui.bridge import BridgeApi


class FakeService:
    def list_devices(self):
        return []

    def list_apps(self, device_id: str):
        return []

    def start_session(self, device_id: str, package_name: str):
        return SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="采集中",
        )

    def stop_session(self):
        return SessionState(
            phase=SessionPhase.STOPPED,
            selected_device_id="SERIAL1",
            selected_package="com.demo.app",
            selectors_locked=False,
            message="已停止",
        )

    def get_live_snapshot(self):
        return LiveSnapshot(
            session=SessionState(
                phase=SessionPhase.RUNNING,
                selected_device_id="SERIAL1",
                selected_package="com.demo.app",
                selectors_locked=True,
                message="采集中",
            ),
            status=PhoneStatus(
                connection_state="connected",
                device_label="Pixel 8",
                screen_state="on",
                app_state="running",
                battery_level=88,
                temperature_c=33.5,
                last_updated_at="2026-04-24T00:00:00Z",
            ),
            metrics=[],
        )


def test_bridge_serializes_dataclasses_for_frontend():
    bridge = BridgeApi(service=FakeService())

    payload = bridge.get_live_snapshot()

    assert payload["session"]["phase"] == "running"
    assert payload["status"]["device_label"] == "Pixel 8"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/ui/test_bridge.py -q`  
Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'perfengine.ui.bridge'`

- [ ] **Step 3: 编写最小实现**

```python
# src/perfengine/ui/__init__.py
__all__ = ["bridge", "window"]
```

```python
# src/perfengine/ui/bridge.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum


def _to_json_ready(value):
    if is_dataclass(value):
        return {key: _to_json_ready(val) for key, val in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_to_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json_ready(val) for key, val in value.items()}
    return value


class BridgeApi:
    def __init__(self, service):
        self.service = service

    def list_devices(self):
        return _to_json_ready(self.service.list_devices())

    def list_apps(self, device_id: str):
        return _to_json_ready(self.service.list_apps(device_id))

    def start_session(self, device_id: str, package_name: str):
        return _to_json_ready(self.service.start_session(device_id, package_name))

    def stop_session(self):
        return _to_json_ready(self.service.stop_session())

    def get_live_snapshot(self):
        return _to_json_ready(self.service.get_live_snapshot())
```

```python
# src/perfengine/ui/window.py
from __future__ import annotations

from pathlib import Path

import webview


def create_main_window(api) -> None:
    index_path = Path(__file__).resolve().parents[3] / "ui" / "dist" / "index.html"
    webview.create_window(
        title="Android QA Perf",
        url=index_path.as_uri(),
        js_api=api,
        width=1440,
        height=960,
    )
```

```python
# src/perfengine/main.py
from perfengine.android.adb_client import AdbClient
from perfengine.android.app_provider import AppProvider
from perfengine.android.device_provider import DeviceProvider
from perfengine.android.sampler import AndroidSampler
from perfengine.android.status_provider import StatusProvider
from perfengine.app.service import PerfToolService
from perfengine.ui.bridge import BridgeApi
from perfengine.ui.window import create_main_window


def build_service() -> PerfToolService:
    adb_client = AdbClient()
    status_provider = StatusProvider(adb_client)
    return PerfToolService(
        device_provider=DeviceProvider(adb_client),
        app_provider=AppProvider(adb_client),
        collector=AndroidSampler(adb_client=adb_client, status_provider=status_provider),
    )


def main() -> None:
    api = BridgeApi(service=build_service())
    create_main_window(api)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/ui/test_bridge.py -q`  
Expected: PASS，输出为 `1 passed`

- [ ] **Step 5: 提交**

```bash
git add src/perfengine/ui/__init__.py src/perfengine/ui/bridge.py src/perfengine/ui/window.py src/perfengine/main.py tests/ui/test_bridge.py
git commit -m "feat: add desktop bridge and entrypoint"
```

### Task 6: 前端工程骨架与会话 Store

**Files:**
- Create: `ui/package.json`
- Create: `ui/tsconfig.json`
- Create: `ui/vite.config.ts`
- Create: `ui/index.html`
- Create: `ui/src/main.ts`
- Create: `ui/src/types.ts`
- Create: `ui/src/api.ts`
- Create: `ui/src/state/sessionStore.ts`
- Test: `ui/src/state/sessionStore.spec.ts`

- [ ] **Step 1: 写前端 Store 失败测试和工程配置**

```json
// ui/package.json
{
  "name": "perfengine-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "echarts": "^5.5.0",
    "vue": "^3.5.13"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "@vue/test-utils": "^2.4.6",
    "happy-dom": "^15.11.0",
    "typescript": "^5.6.3",
    "vite": "^5.4.8",
    "vitest": "^2.1.3"
  }
}
```

```json
// ui/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Node",
    "strict": true,
    "jsx": "preserve",
    "types": ["vitest/globals"],
    "lib": ["ES2020", "DOM"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue"]
}
```

```ts
// ui/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
  },
})
```

```ts
// ui/src/state/sessionStore.spec.ts
import { describe, expect, it } from 'vitest'
import { createSessionStore } from './sessionStore'


describe('createSessionStore', () => {
  it('locks selectors after session starts', async () => {
    const api = {
      listDevices: async () => [{ device_id: 'SERIAL1', display_name: 'Pixel 8', connection_type: 'usb' }],
      listApps: async () => [{ package_name: 'com.demo.app', display_name: 'com.demo.app' }],
      startSession: async () => ({
        phase: 'running',
        selected_device_id: 'SERIAL1',
        selected_package: 'com.demo.app',
        selectors_locked: true,
        message: '采集中',
      }),
      stopSession: async () => ({
        phase: 'stopped',
        selected_device_id: 'SERIAL1',
        selected_package: 'com.demo.app',
        selectors_locked: false,
        message: '已停止',
      }),
      getLiveSnapshot: async () => ({
        session: {
          phase: 'running',
          selected_device_id: 'SERIAL1',
          selected_package: 'com.demo.app',
          selectors_locked: true,
          message: '采集中',
        },
        status: {
          connection_state: 'connected',
          device_label: 'Pixel 8',
          screen_state: 'on',
          app_state: 'running',
          battery_level: 88,
          temperature_c: 33.5,
          last_updated_at: '2026-04-24T00:00:00Z',
        },
        metrics: [],
      }),
    }

    const store = createSessionStore(api)
    await store.refreshDevices()
    await store.loadApps('SERIAL1')
    await store.start('SERIAL1', 'com.demo.app')

    expect(store.session.phase).toBe('running')
    expect(store.session.selectors_locked).toBe(true)
    expect(store.devices).toHaveLength(1)
    expect(store.apps).toHaveLength(1)
  })
})
```

- [ ] **Step 2: 安装前端依赖**

Run: `npm --prefix ui install`  
Expected: 输出包含 `added`，并生成 `ui/node_modules`

- [ ] **Step 3: 运行测试确认失败**

Run: `npm --prefix ui run test -- sessionStore.spec.ts`  
Expected: FAIL，错误包含 `Failed to resolve import "./sessionStore"`

- [ ] **Step 4: 编写最小实现**

```html
<!-- ui/index.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Android QA Perf</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

```ts
// ui/src/types.ts
export type SessionPhase =
  | 'idle'
  | 'loading_devices'
  | 'loading_apps'
  | 'starting'
  | 'running'
  | 'stopped'
  | 'interrupted'
  | 'error'

export interface DeviceInfo {
  device_id: string
  display_name: string
  connection_type: string
}

export interface AppInfo {
  package_name: string
  display_name: string
}

export interface SessionState {
  phase: SessionPhase
  selected_device_id: string | null
  selected_package: string | null
  selectors_locked: boolean
  message: string
}

export interface PhoneStatus {
  connection_state: string
  device_label: string
  screen_state: string
  app_state: string
  battery_level: number | null
  temperature_c: number | null
  last_updated_at: string
}

export interface MetricPoint {
  timestamp: string
  fps: number | null
  frame_time_ms: number | null
  app_cpu_percent: number | null
  total_cpu_percent: number | null
  memory_mb: number | null
  temperature_c: number | null
  battery_level: number | null
}

export interface LiveSnapshot {
  session: SessionState
  status: PhoneStatus
  metrics: MetricPoint[]
}
```

```ts
// ui/src/api.ts
import type { AppInfo, DeviceInfo, LiveSnapshot, SessionState } from './types'

declare global {
  interface Window {
    pywebview?: {
      api: {
        list_devices: () => Promise<DeviceInfo[]>
        list_apps: (deviceId: string) => Promise<AppInfo[]>
        start_session: (deviceId: string, packageName: string) => Promise<SessionState>
        stop_session: () => Promise<SessionState>
        get_live_snapshot: () => Promise<LiveSnapshot>
      }
    }
  }
}

export const bridgeApi = {
  listDevices: () => window.pywebview!.api.list_devices(),
  listApps: (deviceId: string) => window.pywebview!.api.list_apps(deviceId),
  startSession: (deviceId: string, packageName: string) => window.pywebview!.api.start_session(deviceId, packageName),
  stopSession: () => window.pywebview!.api.stop_session(),
  getLiveSnapshot: () => window.pywebview!.api.get_live_snapshot(),
}
```

```ts
// ui/src/state/sessionStore.ts
import type { AppInfo, DeviceInfo, LiveSnapshot, SessionState } from '../types'

const defaultSession: SessionState = {
  phase: 'idle',
  selected_device_id: null,
  selected_package: null,
  selectors_locked: false,
  message: '',
}

export function createSessionStore(api: {
  listDevices: () => Promise<DeviceInfo[]>
  listApps: (deviceId: string) => Promise<AppInfo[]>
  startSession: (deviceId: string, packageName: string) => Promise<SessionState>
  stopSession: () => Promise<SessionState>
  getLiveSnapshot: () => Promise<LiveSnapshot>
}) {
  const state = {
    devices: [] as DeviceInfo[],
    apps: [] as AppInfo[],
    session: { ...defaultSession },
    snapshot: null as LiveSnapshot | null,
    pollTimer: null as number | null,
  }

  async function refreshDevices() {
    state.devices = await api.listDevices()
  }

  async function loadApps(deviceId: string) {
    state.apps = await api.listApps(deviceId)
  }

  async function start(deviceId: string, packageName: string) {
    state.session = await api.startSession(deviceId, packageName)
  }

  async function stop() {
    state.session = await api.stopSession()
    if (state.pollTimer !== null) {
      window.clearInterval(state.pollTimer)
      state.pollTimer = null
    }
  }

  async function pollOnce() {
    state.snapshot = await api.getLiveSnapshot()
    state.session = state.snapshot.session
  }

  function startPolling() {
    if (state.pollTimer !== null) return
    state.pollTimer = window.setInterval(() => {
      void pollOnce()
    }, 1000)
  }

  return {
    get devices() {
      return state.devices
    },
    get apps() {
      return state.apps
    },
    get session() {
      return state.session
    },
    get snapshot() {
      return state.snapshot
    },
    refreshDevices,
    loadApps,
    start,
    stop,
    pollOnce,
    startPolling,
  }
}
```

```ts
// ui/src/main.ts
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

- [ ] **Step 5: 运行测试确认通过**

Run: `npm --prefix ui run test -- sessionStore.spec.ts`  
Expected: PASS，输出为 `1 passed`

- [ ] **Step 6: 提交**

```bash
git add ui/package.json ui/tsconfig.json ui/vite.config.ts ui/index.html ui/src/main.ts ui/src/types.ts ui/src/api.ts ui/src/state/sessionStore.ts ui/src/state/sessionStore.spec.ts
git commit -m "feat: bootstrap frontend store and api contract"
```

### Task 7: 单页 UI 与固定图表

**Files:**
- Create: `ui/src/App.vue`
- Create: `ui/src/components/ToolbarPanel.vue`
- Create: `ui/src/components/StatusCard.vue`
- Create: `ui/src/components/MetricChart.vue`
- Test: `ui/src/components/ToolbarPanel.spec.ts`

- [ ] **Step 1: 写组件失败测试**

```ts
// ui/src/components/ToolbarPanel.spec.ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ToolbarPanel from './ToolbarPanel.vue'


describe('ToolbarPanel', () => {
  it('disables selectors while session is running', () => {
    const wrapper = mount(ToolbarPanel, {
      props: {
        devices: [{ device_id: 'SERIAL1', display_name: 'Pixel 8', connection_type: 'usb' }],
        apps: [{ package_name: 'com.demo.app', display_name: 'com.demo.app' }],
        selectedDeviceId: 'SERIAL1',
        selectedPackage: 'com.demo.app',
        sessionPhase: 'running',
      },
    })

    const selects = wrapper.findAll('select')
    expect((selects[0].element as HTMLSelectElement).disabled).toBe(true)
    expect((selects[1].element as HTMLSelectElement).disabled).toBe(true)
    expect(wrapper.get('button').text()).toContain('停止采集')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm --prefix ui run test -- ToolbarPanel.spec.ts`  
Expected: FAIL，错误包含 `Failed to resolve import "./ToolbarPanel.vue"`

- [ ] **Step 3: 编写最小实现**

```vue
<!-- ui/src/components/ToolbarPanel.vue -->
<script setup lang="ts">
import type { AppInfo, DeviceInfo, SessionPhase } from '../types'

defineProps<{
  devices: DeviceInfo[]
  apps: AppInfo[]
  selectedDeviceId: string | null
  selectedPackage: string | null
  sessionPhase: SessionPhase
}>()

defineEmits<{
  refresh: []
  'update:selectedDeviceId': [value: string]
  'update:selectedPackage': [value: string]
  start: []
  stop: []
}>()
</script>

<template>
  <section class="toolbar">
    <button @click="$emit('refresh')">刷新设备</button>
    <select
      :disabled="sessionPhase === 'running'"
      :value="selectedDeviceId ?? ''"
      @change="$emit('update:selectedDeviceId', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">请选择设备</option>
      <option v-for="device in devices" :key="device.device_id" :value="device.device_id">
        {{ device.display_name }}
      </option>
    </select>
    <select
      :disabled="sessionPhase === 'running' || !selectedDeviceId"
      :value="selectedPackage ?? ''"
      @change="$emit('update:selectedPackage', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">请选择应用</option>
      <option v-for="app in apps" :key="app.package_name" :value="app.package_name">
        {{ app.display_name }}
      </option>
    </select>
    <button
      v-if="sessionPhase !== 'running'"
      :disabled="!selectedDeviceId || !selectedPackage"
      @click="$emit('start')"
    >
      开始采集
    </button>
    <button v-else @click="$emit('stop')">停止采集</button>
  </section>
</template>

<style scoped>
.toolbar {
  display: grid;
  grid-template-columns: 120px 1fr 1fr 120px;
  gap: 12px;
  align-items: center;
}
</style>
```

```vue
<!-- ui/src/components/StatusCard.vue -->
<script setup lang="ts">
import type { PhoneStatus, SessionState } from '../types'

defineProps<{
  session: SessionState
  status: PhoneStatus | null
}>()
</script>

<template>
  <section class="status-card">
    <h2>当前状态</h2>
    <p>会话状态：{{ session.message || session.phase }}</p>
    <p>设备：{{ status?.device_label ?? '未选择设备' }}</p>
    <p>连接：{{ status?.connection_state ?? 'unknown' }}</p>
    <p>屏幕：{{ status?.screen_state ?? 'unknown' }}</p>
    <p>应用：{{ status?.app_state ?? 'not_selected' }}</p>
    <p>电量：{{ status?.battery_level ?? '未知' }}</p>
    <p>温度：{{ status?.temperature_c ?? '未知' }}</p>
    <p>最近刷新：{{ status?.last_updated_at ?? '未开始' }}</p>
  </section>
</template>

<style scoped>
.status-card {
  padding: 16px;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  background: #ffffff;
}
</style>
```

```vue
<!-- ui/src/components/MetricChart.vue -->
<script setup lang="ts">
import * as echarts from 'echarts'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  title: string
  xAxis: string[]
  values: Array<number | null>
}>()

const container = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function render() {
  if (!container.value) return
  chart ??= echarts.init(container.value)
  chart.setOption({
    title: { text: props.title },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.xAxis },
    yAxis: { type: 'value' },
    series: [{ type: 'line', data: props.values }],
  })
}

onMounted(render)
watch(() => [props.xAxis, props.values], render, { deep: true })
</script>

<template>
  <div ref="container" class="chart"></div>
</template>

<style scoped>
.chart {
  min-height: 240px;
  border: 1px solid #d0d7de;
  border-radius: 12px;
  background: #fff;
}
</style>
```

```vue
<!-- ui/src/App.vue -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { bridgeApi } from './api'
import MetricChart from './components/MetricChart.vue'
import StatusCard from './components/StatusCard.vue'
import ToolbarPanel from './components/ToolbarPanel.vue'
import { createSessionStore } from './state/sessionStore'

const store = createSessionStore(bridgeApi)
const selectedDeviceId = ref<string | null>(null)
const selectedPackage = ref<string | null>(null)

const xAxis = computed(() => store.snapshot?.metrics.map((item) => item.timestamp.slice(11, 19)) ?? [])
const fpsValues = computed(() => store.snapshot?.metrics.map((item) => item.fps) ?? [])
const frameTimeValues = computed(() => store.snapshot?.metrics.map((item) => item.frame_time_ms) ?? [])
const appCpuValues = computed(() => store.snapshot?.metrics.map((item) => item.app_cpu_percent) ?? [])
const totalCpuValues = computed(() => store.snapshot?.metrics.map((item) => item.total_cpu_percent) ?? [])
const memoryValues = computed(() => store.snapshot?.metrics.map((item) => item.memory_mb) ?? [])
const tempValues = computed(() => store.snapshot?.metrics.map((item) => item.temperature_c) ?? [])

async function onRefresh() {
  await store.refreshDevices()
}

async function onSelectDevice(deviceId: string) {
  selectedDeviceId.value = deviceId
  selectedPackage.value = null
  await store.loadApps(deviceId)
}

async function onStart() {
  if (!selectedDeviceId.value || !selectedPackage.value) return
  await store.start(selectedDeviceId.value, selectedPackage.value)
  store.startPolling()
  await store.pollOnce()
}

async function onStop() {
  await store.stop()
}
</script>

<template>
  <main class="page">
    <ToolbarPanel
      :devices="store.devices"
      :apps="store.apps"
      :selected-device-id="selectedDeviceId"
      :selected-package="selectedPackage"
      :session-phase="store.session.phase"
      @refresh="onRefresh"
      @update:selectedDeviceId="onSelectDevice"
      @update:selectedPackage="selectedPackage = $event"
      @start="onStart"
      @stop="onStop"
    />

    <StatusCard :session="store.session" :status="store.snapshot?.status ?? null" />

    <section class="grid">
      <MetricChart title="FPS" :x-axis="xAxis" :values="fpsValues" />
      <MetricChart title="Frame Time" :x-axis="xAxis" :values="frameTimeValues" />
      <MetricChart title="App CPU" :x-axis="xAxis" :values="appCpuValues" />
      <MetricChart title="Total CPU" :x-axis="xAxis" :values="totalCpuValues" />
      <MetricChart title="Memory" :x-axis="xAxis" :values="memoryValues" />
      <MetricChart title="Temperature" :x-axis="xAxis" :values="tempValues" />
    </section>
  </main>
</template>

<style scoped>
.page {
  display: grid;
  gap: 16px;
  padding: 20px;
  background: #f6f8fa;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
</style>
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npm --prefix ui run test -- ToolbarPanel.spec.ts`  
Expected: PASS，输出为 `1 passed`

- [ ] **Step 5: 构建前端静态资源**

Run: `npm --prefix ui run build`  
Expected: PASS，输出包含 `dist/index.html`

- [ ] **Step 6: 提交**

```bash
git add ui/src/App.vue ui/src/components/ToolbarPanel.vue ui/src/components/StatusCard.vue ui/src/components/MetricChart.vue ui/src/components/ToolbarPanel.spec.ts
git commit -m "feat: add single page qa dashboard"
```

### Task 8: 错误状态、恢复逻辑与手工验证文档

**Files:**
- Test: `tests/app/test_error_states.py`
- Create: `docs/manual-tests/android-qa-perf-desktop-mvp.md`
- Modify: `src/perfengine/app/service.py`
- Modify: `src/perfengine/android/status_provider.py`
- Modify: `ui/src/state/sessionStore.ts`

- [ ] **Step 1: 写失败场景测试**

```python
# tests/app/test_error_states.py
from perfengine.app.models import AppInfo, DeviceInfo, SessionPhase
from perfengine.app.service import PerfToolService


class FakeDeviceProvider:
    def __init__(self, devices):
        self._devices = devices

    def list_devices(self):
        return self._devices


class FakeAppProvider:
    def list_apps(self, device_id: str):
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]


class FakeCollector:
    def __init__(self, mode: str):
        self.mode = mode

    def begin(self, device_id: str, package_name: str):
        return None

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        if self.mode == "disconnected":
            raise RuntimeError("device disconnected")
        if self.mode == "no-data":
            return (
                type("Status", (), {
                    "connection_state": "connected",
                    "device_label": device_id,
                    "screen_state": "on",
                    "app_state": "running",
                    "battery_level": 80,
                    "temperature_c": 32.0,
                    "last_updated_at": "2026-04-24T00:00:00Z",
                })(),
                None,
            )
        raise RuntimeError("app exited")


def test_no_device_returns_operator_message():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("no-data"),
    )

    devices = service.list_devices()

    assert devices == []
    assert service.state.message == "未检测到 Android 设备"


def test_waiting_for_data_keeps_running_state():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([DeviceInfo(device_id="SERIAL1", display_name="Pixel 8", connection_type="usb")]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("no-data"),
    )

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.RUNNING
    assert snapshot.session.message == "等待设备数据中"


def test_device_disconnect_interrupts_session():
    service = PerfToolService(
        device_provider=FakeDeviceProvider([DeviceInfo(device_id="SERIAL1", display_name="Pixel 8", connection_type="usb")]),
        app_provider=FakeAppProvider(),
        collector=FakeCollector("disconnected"),
    )

    service.start_session("SERIAL1", "com.demo.app")
    snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.INTERRUPTED
    assert snapshot.session.message == "设备已断开"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/app/test_error_states.py -q`  
Expected: FAIL，至少一个断言失败，因为当前服务层还没有处理空设备、无数据、断连消息

- [ ] **Step 3: 编写最小实现**

```python
# src/perfengine/app/service.py
from __future__ import annotations

from datetime import datetime, timezone

from perfengine.app.models import LiveSnapshot, PhoneStatus, SessionPhase, SessionState


class PerfToolService:
    def __init__(self, device_provider, app_provider, collector):
        self.device_provider = device_provider
        self.app_provider = app_provider
        self.collector = collector
        self.history = []
        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=None,
            selected_package=None,
            selectors_locked=False,
            message="",
        )
        self.status = PhoneStatus(
            connection_state="disconnected",
            device_label="",
            screen_state="unknown",
            app_state="not_selected",
            battery_level=None,
            temperature_c=None,
            last_updated_at=self._now(),
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_devices(self):
        if self.device_provider is None:
            return []
        self.state.phase = SessionPhase.LOADING_DEVICES
        devices = self.device_provider.list_devices()
        if not devices:
            self.state = SessionState(
                phase=SessionPhase.IDLE,
                selected_device_id=None,
                selected_package=None,
                selectors_locked=False,
                message="未检测到 Android 设备",
            )
            return []
        self.state.phase = SessionPhase.IDLE
        self.state.message = ""
        return devices

    def list_apps(self, device_id: str):
        if self.app_provider is None:
            return []
        self.state.phase = SessionPhase.LOADING_APPS
        apps = self.app_provider.list_apps(device_id)
        self.state.phase = SessionPhase.IDLE
        self.state.selected_device_id = device_id
        return apps

    def start_session(self, device_id: str, package_name: str) -> SessionState:
        self.state = SessionState(
            phase=SessionPhase.STARTING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="正在启动采集",
        )
        try:
            self.collector.begin(device_id, package_name)
        except Exception:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message="采集启动失败，请重试",
            )
            return self.state

        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="采集中",
        )
        return self.state

    def stop_session(self) -> SessionState:
        self.collector.stop()
        self.state = SessionState(
            phase=SessionPhase.STOPPED,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="已停止",
        )
        return self.state

    def get_live_snapshot(self) -> LiveSnapshot:
        if self.state.phase is SessionPhase.RUNNING:
            try:
                status, point = self.collector.read(self.state.selected_device_id, self.state.selected_package)
                self.status = status
                if point is None:
                    self.state.message = "等待设备数据中"
                else:
                    self.state.message = "采集中"
                    self.history.append(point)
                    self.history = self.history[-60:]
            except RuntimeError as exc:
                message = "设备已断开" if "disconnected" in str(exc) else "目标应用已退出"
                self.state = SessionState(
                    phase=SessionPhase.INTERRUPTED,
                    selected_device_id=self.state.selected_device_id,
                    selected_package=self.state.selected_package,
                    selectors_locked=False,
                    message=message,
                )
        return LiveSnapshot(session=self.state, status=self.status, metrics=self.history)
```

```ts
// ui/src/state/sessionStore.ts
import type { AppInfo, DeviceInfo, LiveSnapshot, SessionState } from '../types'

const defaultSession: SessionState = {
  phase: 'idle',
  selected_device_id: null,
  selected_package: null,
  selectors_locked: false,
  message: '',
}

export function createSessionStore(api: {
  listDevices: () => Promise<DeviceInfo[]>
  listApps: (deviceId: string) => Promise<AppInfo[]>
  startSession: (deviceId: string, packageName: string) => Promise<SessionState>
  stopSession: () => Promise<SessionState>
  getLiveSnapshot: () => Promise<LiveSnapshot>
}) {
  const state = {
    devices: [] as DeviceInfo[],
    apps: [] as AppInfo[],
    session: { ...defaultSession },
    snapshot: null as LiveSnapshot | null,
    errorMessage: '',
    pollTimer: null as number | null,
  }

  async function refreshDevices() {
    state.devices = await api.listDevices()
    if (state.devices.length === 0) {
      state.errorMessage = '未检测到 Android 设备'
    } else {
      state.errorMessage = ''
    }
  }

  async function loadApps(deviceId: string) {
    state.apps = await api.listApps(deviceId)
  }

  async function start(deviceId: string, packageName: string) {
    state.session = await api.startSession(deviceId, packageName)
  }

  async function stop() {
    state.session = await api.stopSession()
    if (state.pollTimer !== null) {
      window.clearInterval(state.pollTimer)
      state.pollTimer = null
    }
  }

  async function pollOnce() {
    state.snapshot = await api.getLiveSnapshot()
    state.session = state.snapshot.session
    if (state.session.phase === 'interrupted' || state.session.phase === 'error') {
      state.errorMessage = state.session.message
      if (state.pollTimer !== null) {
        window.clearInterval(state.pollTimer)
        state.pollTimer = null
      }
    }
  }

  function startPolling() {
    if (state.pollTimer !== null) return
    state.pollTimer = window.setInterval(() => {
      void pollOnce()
    }, 1000)
  }

  return {
    get devices() {
      return state.devices
    },
    get apps() {
      return state.apps
    },
    get session() {
      return state.session
    },
    get snapshot() {
      return state.snapshot
    },
    get errorMessage() {
      return state.errorMessage
    },
    refreshDevices,
    loadApps,
    start,
    stop,
    pollOnce,
    startPolling,
  }
}
```

```markdown
# Android QA 桌面性能 MVP 手工验证清单

## 启动前准备

1. Windows 主机已安装 Python 3.11、Node.js 20 和 ADB。
2. Android 设备已打开开发者模式和 USB 调试。
3. 运行 `python -m pip install -e .[dev]`。
4. 运行 `npm --prefix ui install && npm --prefix ui run build`。

## 验证项

1. 启动 `python -m perfengine.main`，无设备时页面显示“未检测到 Android 设备”。
2. 连接设备后点击“刷新设备”，下拉框中出现机型名。
3. 选择设备后，应用列表出现 `package_name` 列表。
4. 选择应用后点击“开始采集”，设备和应用下拉框变为禁用。
5. 采集中每秒刷新 FPS、Frame Time、App CPU、Total CPU、Memory、Temperature 图表。
6. 状态卡同步显示连接状态、屏幕状态、应用状态、电量、温度和最近刷新时间。
7. 点击“停止采集”，图表停止刷新且保留最后一屏数据。
8. 运行中拔线，页面提示“设备已断开”。
9. 运行中手动关闭应用，页面提示“目标应用已退出”。
10. 采集中锁屏，状态卡展示 `screen_state=off` 或 `unknown`，但页面不崩溃。
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/app/test_error_states.py -q`  
Expected: PASS，输出为 `3 passed`

- [ ] **Step 5: 运行后端全量测试**

Run: `python -m pytest tests -q`  
Expected: PASS，输出为 `13 passed` 或更高，且没有 `FAILED`

- [ ] **Step 6: 提交**

```bash
git add src/perfengine/app/service.py ui/src/state/sessionStore.ts tests/app/test_error_states.py docs/manual-tests/android-qa-perf-desktop-mvp.md
git commit -m "feat: add operator error states and manual verification checklist"
```

## 实施顺序说明

1. 先完成 Task 1 和 Task 2，把领域模型和状态机钉死。
2. 再做 Task 3 和 Task 4，把 Android 侧数据源与统一快照打通。
3. 之后做 Task 5 和 Task 6，让桌面桥和前端状态契约对齐。
4. 最后做 Task 7 和 Task 8，把 QA 可用性、错误提示和手工验收补齐。

## 计划自检

- `android-session-control` 的单设备、单会话、启动失败恢复、停止后恢复控件，分别由 Task 2、Task 5、Task 8 覆盖。
- `android-live-visibility` 的固定图表、状态卡、轮询刷新、运行中断提示，分别由 Task 4、Task 6、Task 7、Task 8 覆盖。
- 计划中没有 `TBD`、`TODO`、`implement later` 之类占位词。
- 所有关键命名在任务间保持一致：`SessionState`、`LiveSnapshot`、`PerfToolService`、`AndroidSampler`、`BridgeApi`、`createSessionStore`。
