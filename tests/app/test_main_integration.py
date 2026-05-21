from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, Platform, SessionPhase
from perfengine.main import build_service


class FakeDeviceProvider:
    def __init__(self, device: DeviceInfo):
        self.device = device

    def list_devices(self):
        return [self.device]


class FakeAppProvider:
    def __init__(self, platform: Platform):
        self.platform = platform

    def list_apps(self, device_id: str):
        return [AppInfo(package_name=f"{device_id}.app", display_name=f"{device_id}.app", platform=self.platform)]


class FakeCollector:
    def __init__(self, platform: Platform):
        self.platform = platform
        self.started = []

    def begin(self, device_id: str, package_name: str):
        self.started.append((device_id, package_name))

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        return PhoneStatus(platform=self.platform, connection_state="connected", app_state="running"), None


def test_build_service_registers_android_and_ios_backends():
    ios_collector = FakeCollector(Platform.IOS)
    service = build_service(
        android_device_provider=FakeDeviceProvider(
            DeviceInfo(device_id="android-1", display_name="Pixel", platform=Platform.ANDROID)
        ),
        android_app_provider=FakeAppProvider(Platform.ANDROID),
        android_collector=FakeCollector(Platform.ANDROID),
        ios_device_provider=FakeDeviceProvider(
            DeviceInfo(device_id="ios-1", display_name="iPhone", platform=Platform.IOS)
        ),
        ios_app_provider=FakeAppProvider(Platform.IOS),
        ios_collector=ios_collector,
    )

    devices = service.list_devices()
    apps = service.list_apps("ios-1")
    state = service.start_session("ios-1", apps[0].package_name)

    assert [device.platform for device in devices] == [Platform.ANDROID, Platform.IOS]
    assert apps[0].platform is Platform.IOS
    assert state.phase is SessionPhase.RUNNING
    assert ios_collector.started == [("ios-1", "ios-1.app")]

