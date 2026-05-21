from pathlib import Path

from perfengine.ios.client import IOSCommandResult, IOSClient
from perfengine.ios.tooling import IOSTooling
from perfengine.ios.tunnel import IOSTunnelManager


def create_tooling(tmp_path: Path) -> IOSTooling:
    assets_dir = tmp_path / "assets" / "ios"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "ios.exe").write_text("", encoding="utf-8")
    (assets_dir / "sib.exe").write_text("", encoding="utf-8")
    return IOSTooling(root_dir=tmp_path)


def test_client_uses_bundled_sib_path_for_app_list(tmp_path: Path):
    calls = []
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        runner=lambda cmd: calls.append(cmd)
        or IOSCommandResult(
            returncode=0,
            stdout='{"apps":[{"CFBundleIdentifier":"com.example.app","CFBundleDisplayName":"Example"}]}',
        ),
    )

    apps = client.list_apps("UDID1")

    assert calls[0][0] == str(tmp_path / "assets" / "ios" / "sib.exe")
    assert calls[0][1:] == ["app", "list", "-u", "UDID1", "-j"]
    assert apps[0]["CFBundleIdentifier"] == "com.example.app"


def test_client_parses_sib_app_list_array_output(tmp_path: Path):
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        runner=lambda cmd: IOSCommandResult(
            returncode=0,
            stdout=(
                '{"bundleId":"com.example.alpha","name":"Alpha"}\n'
                '{"bundleId":"com.example.beta","name":"Beta"}\n'
            ),
        ),
    )

    apps = client.list_apps("UDID1")

    assert apps == [
        {"bundleId": "com.example.alpha", "name": "Alpha"},
        {"bundleId": "com.example.beta", "name": "Beta"},
    ]


def test_client_parses_sib_app_list_with_non_ascii_names(tmp_path: Path):
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        runner=lambda cmd: IOSCommandResult(
            returncode=0,
            stdout=(
                '{"shortVersion":"1.4.11","version":"26050701","name":"二重螺旋","bundleId":"com.hero.dna.ios"}\n'
                '{"shortVersion":"7.43.17","version":"446938450","name":"飞书","bundleId":"com.bytedance.ee.lark"}\n'
            ),
        ),
    )

    apps = client.list_apps("UDID1")

    assert apps[0]["name"] == "二重螺旋"
    assert apps[1]["bundleId"] == "com.bytedance.ee.lark"


def test_client_treats_missing_stdout_as_empty_app_list(tmp_path: Path):
    client = IOSClient(
        tooling=create_tooling(tmp_path),
        tunnel_manager=IOSTunnelManager(create_tooling(tmp_path), probe=lambda device_id: True),
        runner=lambda cmd: IOSCommandResult(returncode=0, stdout=None),
    )

    assert client.list_apps("UDID1") == []


def test_client_prepare_starts_tunnel_manager():
    calls = []

    class FakeTunnel:
        def ensure_ready(self, device_id: str, *, os_version: str | None = None):
            calls.append((device_id, os_version))

    client = IOSClient(tooling=IOSTooling(root_dir=Path(".")), tunnel_manager=FakeTunnel(), runner=lambda cmd: None)

    client.prepare("UDID1")

    assert calls == [("UDID1", None)]
