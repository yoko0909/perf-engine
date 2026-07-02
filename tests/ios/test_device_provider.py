import pytest

from perfengine.app.errors import OperatorError
from perfengine.app.models import Platform
from perfengine.ios.device_provider import IOSDeviceProvider


class FakeDeviceAdapter:
    def __init__(self, devices=None, error=None):
        self.devices = devices if devices is not None else []
        self.error = error
        self.calls = 0

    def list_devices(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.devices


def test_device_provider_uses_pymobiledevice_adapter_for_device_discovery():
    adapter = FakeDeviceAdapter(
        [
            {
                "Identifier": "00008110-0012345601E8001E",
                "DeviceName": "QA iPhone",
                "ConnectionType": "USB",
            }
        ]
    )
    provider = IOSDeviceProvider(device_adapter=adapter)

    devices = provider.list_devices()

    assert adapter.calls == 1
    assert devices[0].device_id == "00008110-0012345601E8001E"
    assert devices[0].display_name == "QA iPhone"
    assert devices[0].connection_type == "usb"
    assert devices[0].platform is Platform.IOS
    assert devices[0].os_version is None


def test_device_provider_returns_empty_list_when_no_ios_device():
    provider = IOSDeviceProvider(device_adapter=FakeDeviceAdapter([]))

    assert provider.list_devices() == []


def test_device_provider_accepts_pymobiledevice_short_info_fields():
    provider = IOSDeviceProvider(
        device_adapter=FakeDeviceAdapter(
            [
                {
                    "udid": "00008110-00062DD21AFB801E",
                    "DeviceName": "QA iPhone",
                    "ProductType": "iPhone14,5",
                    "ProductVersion": "18.3",
                    "ConnectionType": "USB",
                }
            ]
        )
    )

    devices = provider.list_devices()

    assert devices[0].device_id == "00008110-00062DD21AFB801E"
    assert devices[0].display_name == "QA iPhone"
    assert devices[0].platform is Platform.IOS
    assert devices[0].os_version == "18.3"


def test_device_provider_propagates_operator_safe_pymobiledevice_errors():
    provider = IOSDeviceProvider(
        device_adapter=FakeDeviceAdapter(
            error=OperatorError(
                code="ios_pairing_required",
                message="Unlock the iPhone, trust this computer, and try again.",
            )
        )
    )

    with pytest.raises(OperatorError) as exc_info:
        provider.list_devices()

    assert exc_info.value.code == "ios_pairing_required"
