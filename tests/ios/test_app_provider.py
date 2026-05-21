from perfengine.app.models import Platform
from perfengine.ios.app_provider import IOSAppProvider


class FakeIOSClient:
    def __init__(self):
        self.prepared = []

    def prepare(self, device_id: str):
        self.prepared.append(device_id)

    def list_apps(self, device_id: str):
        return [
            {
                "CFBundleIdentifier": "com.example.zeta",
                "CFBundleDisplayName": "Zeta",
            },
            {
                "packageName": "com.example.alpha",
                "name": "Alpha",
            },
            {
                "CFBundleIdentifier": "",
                "CFBundleDisplayName": "Broken",
            },
        ]


def test_app_provider_does_not_require_tunnel_before_listing_apps():
    client = FakeIOSClient()
    provider = IOSAppProvider(client)

    provider.list_apps("UDID1")

    assert client.prepared == []


def test_app_provider_maps_ios_apps_and_sorts_by_display_name():
    provider = IOSAppProvider(FakeIOSClient())

    apps = provider.list_apps("UDID1")

    assert [app.display_name for app in apps] == ["Alpha", "Zeta"]
    assert [app.package_name for app in apps] == ["com.example.alpha", "com.example.zeta"]
    assert all(app.platform is Platform.IOS for app in apps)
