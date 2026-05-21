from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, Platform, SessionPhase
from perfengine.app.platforms import PlatformRegistry
from perfengine.app.service import PerfToolService


class FakeProvider:
    def __init__(self, devices):
        self.devices = devices

    def list_devices(self):
        return self.devices

    def list_apps(self, device_id: str):
        return [
            AppInfo(
                package_name=f"{device_id}.app",
                display_name=f"{device_id}.app",
            )
        ]


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
        provider=FakeProvider(
            [DeviceInfo(device_id="android-1", display_name="Pixel", platform=Platform.ANDROID)]
        ),
        collector=FakeCollector(Platform.ANDROID),
    )
    registry.register(
        Platform.IOS,
        provider=FakeProvider(
            [DeviceInfo(device_id="ios-1", display_name="iPhone", platform=Platform.IOS)]
        ),
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
        provider=FakeProvider(
            [DeviceInfo(device_id="android-1", display_name="Pixel", platform=Platform.ANDROID)]
        ),
        collector=FakeCollector(Platform.ANDROID),
    )
    registry.register(
        Platform.IOS,
        provider=FakeProvider(
            [DeviceInfo(device_id="ios-1", display_name="iPhone", platform=Platform.IOS)]
        ),
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
