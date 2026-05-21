from pathlib import Path

import pytest

from perfengine.app.errors import OperatorError
from perfengine.app.models import Platform
from perfengine.ios.device_provider import IOSCommandResult, IOSDeviceProvider
from perfengine.ios.tooling import IOSTooling


def create_tooling(tmp_path: Path) -> IOSTooling:
    assets_dir = tmp_path / "assets" / "ios"
    assets_dir.mkdir(parents=True)
    (assets_dir / "ios.exe").write_text("", encoding="utf-8")
    (assets_dir / "sib.exe").write_text("", encoding="utf-8")
    return IOSTooling(root_dir=tmp_path)


def test_device_provider_parses_go_ios_details_output(tmp_path: Path):
    provider = IOSDeviceProvider(
        create_tooling(tmp_path),
        runner=lambda cmd: IOSCommandResult(
            returncode=0,
            stdout=(
                '{"devices":[{'
                '"Identifier":"00008110-0012345601E8001E",'
                '"Name":"QA iPhone",'
                '"ConnectionType":"USB"'
                "}]}"
            ),
        ),
    )

    devices = provider.list_devices()

    assert devices[0].device_id == "00008110-0012345601E8001E"
    assert devices[0].display_name == "QA iPhone"
    assert devices[0].connection_type == "usb"
    assert devices[0].platform is Platform.IOS


def test_device_provider_returns_empty_list_when_no_ios_device(tmp_path: Path):
    provider = IOSDeviceProvider(
        create_tooling(tmp_path),
        runner=lambda cmd: IOSCommandResult(returncode=0, stdout='{"devices":[]}'),
    )

    assert provider.list_devices() == []


def test_device_provider_parses_go_ios_warning_plus_device_list_output(tmp_path: Path):
    provider = IOSDeviceProvider(
        create_tooling(tmp_path),
        runner=lambda cmd: IOSCommandResult(
            returncode=0,
            stdout=(
                '{"level":"warning","msg":"go-ios agent is not running.","time":"2026-05-21T22:55:03+08:00"}\n'
                '{"deviceList":[{'
                '"Udid":"00008110-00062DD21AFB801E",'
                '"ProductName":"iPhone OS",'
                '"ProductType":"iPhone14,5",'
                '"ProductVersion":"18.3"'
                "}]}"
            ),
        ),
    )

    devices = provider.list_devices()

    assert devices[0].device_id == "00008110-00062DD21AFB801E"
    assert devices[0].display_name == "iPhone OS"
    assert devices[0].platform is Platform.IOS


def test_device_provider_reports_untrusted_device(tmp_path: Path):
    provider = IOSDeviceProvider(
        create_tooling(tmp_path),
        runner=lambda cmd: IOSCommandResult(returncode=1, stdout="", stderr="pair record missing trust"),
    )

    with pytest.raises(OperatorError) as exc_info:
        provider.list_devices()

    assert exc_info.value.code == "ios_device_not_trusted"


def test_device_provider_reports_invalid_json(tmp_path: Path):
    provider = IOSDeviceProvider(
        create_tooling(tmp_path),
        runner=lambda cmd: IOSCommandResult(returncode=0, stdout="not json"),
    )

    with pytest.raises(OperatorError) as exc_info:
        provider.list_devices()

    assert exc_info.value.code == "ios_device_list_invalid"
