from __future__ import annotations

from perfengine.app.errors import OperatorError
from perfengine.app.models import (
    LiveSnapshot,
    PhoneStatus,
    SessionPhase,
    SessionState,
)


class PerfToolService:
    def __init__(
        self,
        device_provider,
        app_provider,
        collector,
        *,
        history_limit: int = 60,
    ) -> None:
        self.device_provider = device_provider
        self.app_provider = app_provider
        self.collector = collector
        self.history_limit = history_limit
        self.history = []
        self.status = PhoneStatus()
        self.state = SessionState(phase=SessionPhase.IDLE)
        self._devices_by_id: dict[str, str] = {}

    def list_devices(self):
        self.state = SessionState(
            phase=SessionPhase.LOADING_DEVICES,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="正在刷新设备",
        )
        try:
            devices = self.device_provider.list_devices()
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=None,
                selected_package=None,
                selectors_locked=False,
                message=exc.message,
            )
            return []

        self._devices_by_id = {item.device_id: item.display_name for item in devices}
        if not devices:
            self.status = PhoneStatus()
            self.state = SessionState(
                phase=SessionPhase.IDLE,
                selected_device_id=None,
                selected_package=None,
                selectors_locked=False,
                message="未检测到 Android 设备",
            )
            return []

        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="",
        )
        return devices

    def list_apps(self, device_id: str):
        self.state = SessionState(
            phase=SessionPhase.LOADING_APPS,
            selected_device_id=device_id,
            selected_package=None,
            selectors_locked=False,
            message="正在加载应用",
        )
        try:
            apps = self.app_provider.list_apps(device_id)
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=None,
                selectors_locked=False,
                message=exc.message,
            )
            return []

        self.status.device_label = self._devices_by_id.get(device_id, device_id)
        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=device_id,
            selected_package=None,
            selectors_locked=False,
            message="",
        )
        return apps

    def start_session(self, device_id: str, package_name: str) -> SessionState:
        self.state = SessionState(
            phase=SessionPhase.STARTING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="正在启动采集",
        )
        self.status.device_label = self._devices_by_id.get(device_id, device_id)
        try:
            self.collector.begin(device_id, package_name)
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message=exc.message,
            )
            return self.state
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
        try:
            self.collector.stop()
        except Exception:
            pass

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
            self._refresh_running_snapshot()
        return LiveSnapshot(session=self.state, status=self.status, metrics=list(self.history))

    def _refresh_running_snapshot(self) -> None:
        try:
            status, point = self.collector.read(
                self.state.selected_device_id,
                self.state.selected_package,
            )
        except RuntimeError as exc:
            message = "设备已断开" if "disconnected" in str(exc) else "目标应用已退出"
            self.state = SessionState(
                phase=SessionPhase.INTERRUPTED,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message=message,
            )
            return
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message=exc.message,
            )
            return

        self.status = status
        self.status.device_label = self.status.device_label or self._devices_by_id.get(
            self.state.selected_device_id or "",
            self.state.selected_device_id or "",
        )

        if status.connection_state != "connected":
            self.state = SessionState(
                phase=SessionPhase.INTERRUPTED,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message="设备已断开",
            )
            return

        if status.app_state != "running":
            self.state = SessionState(
                phase=SessionPhase.INTERRUPTED,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message="目标应用已退出",
            )
            return

        if point is None:
            self.state = SessionState(
                phase=SessionPhase.RUNNING,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=True,
                message="等待设备数据中",
            )
            return

        self.history.append(point)
        self.history = self.history[-self.history_limit :]
        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=True,
            message="采集中",
        )
