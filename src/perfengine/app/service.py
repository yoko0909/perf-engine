from __future__ import annotations

from perfengine.app.errors import OperatorError
from perfengine.app.models import (
    LiveSnapshot,
    PhoneStatus,
    Platform,
    SessionPhase,
    SessionState,
)


class PerfToolService:
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

    def list_devices(self):
        self.state = SessionState(
            phase=SessionPhase.LOADING_DEVICES,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="Refreshing devices.",
            platform=self.state.platform,
        )
        try:
            devices = self._list_devices()
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
                message="No supported devices were detected.",
            )
            return []

        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="",
            platform=self.state.platform,
        )
        return devices

    def list_apps(self, device_id: str):
        platform = self._platform_for_device(device_id)
        self.state = SessionState(
            phase=SessionPhase.LOADING_APPS,
            selected_device_id=device_id,
            selected_package=None,
            selectors_locked=False,
            message="Loading applications.",
            platform=platform,
        )
        try:
            apps = self._app_provider_for(device_id).list_apps(device_id)
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=None,
                selectors_locked=False,
                message=exc.message,
                platform=platform,
            )
            return []

        for app in apps:
            if platform is not None:
                app.platform = platform
        self.status.device_label = self._devices_by_id.get(device_id, device_id)
        self.status.platform = platform
        self.state = SessionState(
            phase=SessionPhase.IDLE,
            selected_device_id=device_id,
            selected_package=None,
            selectors_locked=False,
            message="",
            platform=platform,
        )
        return apps

    def start_session(self, device_id: str, package_name: str) -> SessionState:
        platform = self._platform_for_device(device_id)
        self.state = SessionState(
            phase=SessionPhase.STARTING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="Starting collection.",
            platform=platform,
        )
        self.status.device_label = self._devices_by_id.get(device_id, device_id)
        self.status.platform = platform
        try:
            self._collector_for(device_id).begin(device_id, package_name)
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message=exc.message,
                platform=platform,
            )
            return self.state
        except Exception:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=device_id,
                selected_package=package_name,
                selectors_locked=False,
                message="Collection could not be started.",
                platform=platform,
            )
            return self.state

        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=device_id,
            selected_package=package_name,
            selectors_locked=True,
            message="Collection is running.",
            platform=platform,
        )
        return self.state

    def stop_session(self) -> SessionState:
        try:
            self._collector_for(self.state.selected_device_id).stop()
        except Exception:
            pass

        self.state = SessionState(
            phase=SessionPhase.STOPPED,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=False,
            message="Collection stopped.",
            platform=self.state.platform,
        )
        return self.state

    def get_live_snapshot(self) -> LiveSnapshot:
        if self.state.phase is SessionPhase.RUNNING:
            self._refresh_running_snapshot()
        return LiveSnapshot(session=self.state, status=self.status, metrics=list(self.history))

    def _refresh_running_snapshot(self) -> None:
        try:
            status, point = self._collector_for(self.state.selected_device_id).read(
                self.state.selected_device_id,
                self.state.selected_package,
            )
        except RuntimeError as exc:
            message = (
                "Device disconnected during collection."
                if "disconnected" in str(exc)
                else "Target application exited during collection."
            )
            self.state = SessionState(
                phase=SessionPhase.INTERRUPTED,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message=message,
                platform=self.state.platform,
            )
            return
        except OperatorError as exc:
            self.state = SessionState(
                phase=SessionPhase.ERROR,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message=exc.message,
                platform=self.state.platform,
            )
            return

        self.status = status
        self.status.platform = self.status.platform or self.state.platform
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
                message="Device disconnected during collection.",
                platform=self.state.platform,
            )
            return

        if status.app_state != "running":
            self.state = SessionState(
                phase=SessionPhase.INTERRUPTED,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=False,
                message="Target application exited during collection.",
                platform=self.state.platform,
            )
            return

        if point is None:
            self.state = SessionState(
                phase=SessionPhase.RUNNING,
                selected_device_id=self.state.selected_device_id,
                selected_package=self.state.selected_package,
                selectors_locked=True,
                message=self.status.status_notice or "Waiting for device data.",
                platform=self.state.platform,
            )
            return

        self.history.append(point)
        self.history = self.history[-self.history_limit :]
        self.state = SessionState(
            phase=SessionPhase.RUNNING,
            selected_device_id=self.state.selected_device_id,
            selected_package=self.state.selected_package,
            selectors_locked=True,
            message=self.status.status_notice or "Collection is running.",
            platform=self.state.platform,
        )

    def _list_devices(self):
        if self.platform_registry is not None:
            return self.platform_registry.list_devices()
        return self.device_provider.list_devices()

    def _platform_for_device(self, device_id: str | None) -> Platform | None:
        if self.platform_registry is None or device_id is None:
            return None
        return self.platform_registry.platform_for_device(device_id)

    def _app_provider_for(self, device_id: str):
        if self.platform_registry is not None:
            return self.platform_registry.provider_for_device(device_id)
        return self.app_provider

    def _collector_for(self, device_id: str | None):
        if self.platform_registry is not None and device_id is not None:
            return self.platform_registry.collector_for_device(device_id)
        return self.collector
