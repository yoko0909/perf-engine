from pathlib import Path
from io import BytesIO

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSTooling
from perfengine.ios.tunnel import IOSTunnelManager


class FakeProcess:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True


def create_tooling(tmp_path: Path) -> IOSTooling:
    assets_dir = tmp_path / "assets" / "ios"
    assets_dir.mkdir(parents=True)
    (assets_dir / "ios.exe").write_text("", encoding="utf-8")
    (assets_dir / "sib.exe").write_text("", encoding="utf-8")
    return IOSTooling(root_dir=tmp_path)


def test_requires_tunnel_for_ios_17_and_unknown_versions():
    assert IOSTunnelManager.requires_tunnel("17.0") is True
    assert IOSTunnelManager.requires_tunnel(None) is True
    assert IOSTunnelManager.requires_tunnel("16.7") is False


def test_ensure_ready_starts_host_side_tunnel_for_ios_17(tmp_path: Path):
    calls = {"popen": [], "probe": 0}

    def fake_probe(device_id: str) -> bool:
        calls["probe"] += 1
        return calls["probe"] > 1

    manager = IOSTunnelManager(
        create_tooling(tmp_path),
        popen=lambda cmd: calls["popen"].append(cmd) or FakeProcess(),
        probe=fake_probe,
        sleep=lambda seconds: None,
    )

    manager.ensure_ready("UDID1", os_version="17.2")

    assert calls["popen"][0][-3:] == ["tunnel", "start", "--userspace"]


def test_ensure_ready_skips_tunnel_for_ios_16(tmp_path: Path):
    manager = IOSTunnelManager(
        create_tooling(tmp_path),
        popen=lambda cmd: pytest.fail("tunnel should not start"),
        probe=lambda device_id: False,
    )

    manager.ensure_ready("UDID1", os_version="16.7")


def test_ensure_ready_reports_timeout(tmp_path: Path):
    manager = IOSTunnelManager(
        create_tooling(tmp_path),
        popen=lambda cmd: FakeProcess(),
        probe=lambda device_id: False,
        sleep=lambda seconds: None,
        timeout_s=0.01,
        poll_interval_s=0.01,
    )

    with pytest.raises(OperatorError) as exc_info:
        manager.ensure_ready("UDID1", os_version="17.2")

    assert exc_info.value.code == "ios_tunnel_unavailable"


def test_default_probe_reads_go_ios_tunnel_http_endpoint(tmp_path: Path):
    def fake_urlopen(url: str, timeout: float):
        assert url == "http://127.0.0.1:60105/tunnels"
        assert timeout == 1.0
        return BytesIO(b'[{"udid":"UDID1","address":"fd00::1"}]')

    manager = IOSTunnelManager(create_tooling(tmp_path), urlopen=fake_urlopen)

    assert manager.probe("UDID1") is True
    assert manager.probe("OTHER") is False
