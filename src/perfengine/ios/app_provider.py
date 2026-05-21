from __future__ import annotations

from typing import Any

from perfengine.app.models import AppInfo, Platform


class IOSAppProvider:
    def __init__(self, ios_client) -> None:
        self.ios_client = ios_client

    def list_apps(self, device_id: str) -> list[AppInfo]:
        apps = [self._to_app_info(item) for item in self.ios_client.list_apps(device_id)]
        apps = [app for app in apps if app is not None]
        apps.sort(key=lambda item: item.display_name.lower())
        return apps

    @staticmethod
    def _to_app_info(item: dict[str, Any]) -> AppInfo | None:
        package_name = IOSAppProvider._first_text(
            item,
            "packageName",
            "CFBundleIdentifier",
            "bundleIdentifier",
            "bundleId",
            "bundle_id",
            default="",
        )
        if not package_name:
            return None
        display_name = IOSAppProvider._first_text(
            item,
            "name",
            "CFBundleDisplayName",
            "CFBundleName",
            default=package_name,
        )
        return AppInfo(
            package_name=package_name,
            display_name=display_name,
            platform=Platform.IOS,
        )

    @staticmethod
    def _first_text(item: dict[str, Any], *keys: str, default: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default
