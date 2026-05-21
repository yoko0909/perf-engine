from __future__ import annotations

from perfengine.android.adb_client import AdbClient
from perfengine.android.app_provider import AppProvider
from perfengine.android.device_provider import DeviceProvider
from perfengine.android.sampler import AndroidSampler
from perfengine.android.status_provider import StatusProvider
from perfengine.app.models import Platform
from perfengine.app.platforms import PlatformRegistry
from perfengine.app.service import PerfToolService
from perfengine.ios.app_provider import IOSAppProvider
from perfengine.ios.client import IOSClient
from perfengine.ios.device_provider import IOSDeviceProvider
from perfengine.ios.sampler import IOSSampler
from perfengine.ios.tooling import IOSTooling
from perfengine.ui.bridge import BridgeApi
from perfengine.ui.window import start_window


def build_service(
    *,
    android_device_provider=None,
    android_app_provider=None,
    android_collector=None,
    ios_device_provider=None,
    ios_app_provider=None,
    ios_collector=None,
) -> PerfToolService:
    if android_device_provider is None or android_app_provider is None or android_collector is None:
        adb_client = AdbClient()
        android_device_provider = android_device_provider or DeviceProvider(adb_client)
        android_app_provider = android_app_provider or AppProvider(adb_client)
        status_provider = StatusProvider(adb_client)
        android_collector = android_collector or AndroidSampler(adb_client, status_provider)

    if ios_device_provider is None or ios_app_provider is None or ios_collector is None:
        ios_tooling = IOSTooling()
        ios_client = IOSClient(ios_tooling)
        ios_device_provider = ios_device_provider or IOSDeviceProvider(ios_tooling)
        ios_app_provider = ios_app_provider or IOSAppProvider(ios_client)
        ios_collector = ios_collector or IOSSampler(ios_client)

    registry = PlatformRegistry()
    registry.register(
        Platform.ANDROID,
        device_provider=android_device_provider,
        app_provider=android_app_provider,
        collector=android_collector,
    )
    registry.register(
        Platform.IOS,
        device_provider=ios_device_provider,
        app_provider=ios_app_provider,
        collector=ios_collector,
    )
    return PerfToolService(platform_registry=registry)


def build_application() -> BridgeApi:
    return BridgeApi(build_service())


def main() -> None:
    api = build_application()
    start_window(api)


if __name__ == "__main__":
    main()
