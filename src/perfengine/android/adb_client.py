from __future__ import annotations

import subprocess
from dataclasses import dataclass

from perfengine.app.errors import OperatorError


@dataclass(slots=True)
class AdbCommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


class AdbClient:
    def __init__(self, adb_path: str = "adb", runner=None) -> None:
        self.adb_path = adb_path
        self.runner = runner or self._default_runner

    def _default_runner(self, cmd: list[str]) -> AdbCommandResult:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return AdbCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_raw(self, args: list[str], *, serial: str | None = None):
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        try:
            return self.runner(cmd)
        except FileNotFoundError as exc:
            raise OperatorError(
                code="adb_unavailable",
                message="Android 设备通信不可用",
            ) from exc

    def run(self, args: list[str], *, serial: str | None = None) -> str:
        completed = self.run_raw(args, serial=serial)
        if getattr(completed, "returncode", 1) != 0:
            raise OperatorError(
                code="adb_unavailable",
                message="Android 设备通信不可用",
            )
        return getattr(completed, "stdout", "")

    def try_run(self, args: list[str], *, serial: str | None = None) -> str:
        completed = self.run_raw(args, serial=serial)
        if getattr(completed, "returncode", 1) != 0:
            return ""
        return getattr(completed, "stdout", "")
