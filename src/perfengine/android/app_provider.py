from __future__ import annotations

from perfengine.app.models import AppInfo


class AppProvider:
    def __init__(self, adb_client) -> None:
        self.adb_client = adb_client

    def list_apps(self, device_id: str) -> list[AppInfo]:
        output = self.adb_client.run(
            ["shell", "pm", "list", "packages", "-3"],
            serial=device_id,
        )
        apps: list[AppInfo] = []
        for line in output.splitlines():
            if not line.startswith("package:"):
                continue
            package_name = line.split(":", 1)[1].strip()
            if not package_name:
                continue
            apps.append(
                AppInfo(
                    package_name=package_name,
                    display_name=package_name,
                )
            )
        apps.sort(key=lambda item: item.package_name)
        return apps
