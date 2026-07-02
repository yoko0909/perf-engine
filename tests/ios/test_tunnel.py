from io import BytesIO

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.tunnel import IOSTunnelManager


class FakeProcess:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True


def test_requires_tunnel_for_ios_17_and_unknown_versions():
    assert IOSTunnelManager.requires_tunnel("17.0") is True
    assert IOSTunnelManager.requires_tunnel(None) is True
    assert IOSTunnelManager.requires_tunnel("16.7") is False


def test_ensure_ready_starts_pymobiledevice_tunnel_for_ios_17():
    calls = {"starter": 0, "probe": 0}

    def fake_probe(device_id: str) -> bool:
        calls["probe"] += 1
        return calls["probe"] > 1

    manager = IOSTunnelManager(
        starter=lambda: calls.__setitem__("starter", calls["starter"] + 1) or FakeProcess(),
        probe=fake_probe,
        sleep=lambda seconds: None,
    )

    manager.ensure_ready("UDID1", os_version="17.2")

    assert calls["starter"] == 1


def test_ensure_ready_starts_owned_tunnel_even_when_stale_default_endpoint_answers():
    calls = {"starter": 0}

    manager = IOSTunnelManager(
        starter=lambda: calls.__setitem__("starter", calls["starter"] + 1) or "http://127.0.0.1:5555",
        probe=lambda device_id: True,
    )

    manager.ensure_ready("UDID1", os_version="17.2")

    assert calls["starter"] == 1
    assert manager.tunnel_info_url == "http://127.0.0.1:5555"


def test_ensure_ready_skips_tunnel_for_ios_16():
    manager = IOSTunnelManager(
        starter=lambda: pytest.fail("tunnel should not start"),
        probe=lambda device_id: False,
    )

    manager.ensure_ready("UDID1", os_version="16.7")


def test_ensure_ready_reports_timeout():
    manager = IOSTunnelManager(
        starter=lambda: FakeProcess(),
        probe=lambda device_id: False,
        sleep=lambda seconds: None,
        timeout_s=0.01,
        poll_interval_s=0.01,
    )

    with pytest.raises(OperatorError) as exc_info:
        manager.ensure_ready("UDID1", os_version="17.2")

    assert exc_info.value.code == "ios_tunnel_unavailable"


def test_default_probe_reads_pymobiledevice_tunnel_http_endpoint():
    def fake_urlopen(url: str, timeout: float):
        assert url == "http://127.0.0.1:60105/tunnels"
        assert timeout == 1.0
        return BytesIO(b'[{"udid":"UDID1","address":"fd00::1"}]')

    manager = IOSTunnelManager(urlopen=fake_urlopen)

    assert manager.probe("UDID1") is True
    assert manager.probe("OTHER") is False


def test_starter_url_replaces_probe_endpoint():
    urls = []

    def fake_urlopen(url: str, timeout: float):
        urls.append(url)
        if url == "http://127.0.0.1:5555":
            return BytesIO(b'{"UDID1":{"ip":"fd00::1","port":12345}}')
        return BytesIO(b"{}")

    manager = IOSTunnelManager(
        starter=lambda: "http://127.0.0.1:5555",
        urlopen=fake_urlopen,
        sleep=lambda seconds: None,
    )

    manager.ensure_ready("UDID1", os_version="17.2")

    assert urls[-1] == "http://127.0.0.1:5555"
