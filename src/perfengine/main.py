from __future__ import annotations

from perfengine.android.adb_client import AdbClient
from perfengine.android.app_provider import AppProvider
from perfengine.android.device_provider import DeviceProvider
from perfengine.android.sampler import AndroidSampler
from perfengine.android.status_provider import StatusProvider
from perfengine.app.service import PerfToolService
from perfengine.ui.bridge import BridgeApi
from perfengine.ui.window import start_window


def build_application() -> BridgeApi:
    adb_client = AdbClient()
    device_provider = DeviceProvider(adb_client)
    app_provider = AppProvider(adb_client)
    status_provider = StatusProvider(adb_client)
    collector = AndroidSampler(adb_client, status_provider)
    service = PerfToolService(
        device_provider=device_provider,
        app_provider=app_provider,
        collector=collector,
    )
    return BridgeApi(service)


def main() -> None:
    api = build_application()
    start_window(api)


if __name__ == "__main__":
    main()
