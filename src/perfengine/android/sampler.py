from __future__ import annotations

from perfengine.app.errors import OperatorError
from perfengine.app.models import utc_now_iso
from perfengine.android.metrics import normalize_metric_point


class AndroidSampler:
    def __init__(self, adb_client, status_provider) -> None:
        self.adb_client = adb_client
        self.status_provider = status_provider
        self._active_session: tuple[str, str] | None = None

    def begin(self, device_id: str, package_name: str) -> None:
        status = self.status_provider.get_phone_status(device_id, package_name)
        if status.connection_state != "connected":
            raise OperatorError(
                code="adb_unavailable",
                message="Android 设备通信不可用",
            )
        if status.app_state != "running":
            raise OperatorError(
                code="app_not_running",
                message="目标应用未运行",
            )
        self._active_session = (device_id, package_name)

    def stop(self) -> None:
        self._active_session = None

    def read(self, device_id: str, package_name: str):
        status = self.status_provider.get_phone_status(device_id, package_name)
        if status.connection_state != "connected" or status.app_state != "running":
            return status, None

        cpu_output = self.adb_client.run(
            ["shell", "dumpsys", "cpuinfo"],
            serial=device_id,
        )
        memory_output = self.adb_client.run(
            ["shell", "dumpsys", "meminfo", package_name],
            serial=device_id,
        )
        frame_output = self.adb_client.try_run(
            ["shell", "dumpsys", "gfxinfo", package_name],
            serial=device_id,
        )
        point = normalize_metric_point(
            timestamp=utc_now_iso(),
            package_name=package_name,
            cpu_output=cpu_output,
            memory_output=memory_output,
            frame_output=frame_output,
            status=status,
        )
        return status, point
