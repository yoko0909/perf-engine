from pathlib import Path

import pytest

from perfengine.app.errors import OperatorError
from perfengine.ios.tooling import IOSTooling


def test_tooling_resolves_bundled_ios_assets(tmp_path: Path):
    tooling = IOSTooling(root_dir=tmp_path)

    paths = tooling.paths()

    assert paths.ios == tmp_path / "assets" / "ios" / "ios.exe"
    assert paths.sib == tmp_path / "assets" / "ios" / "sib.exe"


def test_tooling_raises_operator_error_when_assets_are_missing(tmp_path: Path):
    tooling = IOSTooling(root_dir=tmp_path)

    with pytest.raises(OperatorError) as exc_info:
        tooling.require_tools()

    assert exc_info.value.code == "ios_tools_missing"


def test_tooling_accepts_existing_bundled_assets(tmp_path: Path):
    assets_dir = tmp_path / "assets" / "ios"
    assets_dir.mkdir(parents=True)
    (assets_dir / "ios.exe").write_text("", encoding="utf-8")
    (assets_dir / "sib.exe").write_text("", encoding="utf-8")
    tooling = IOSTooling(root_dir=tmp_path)

    paths = tooling.require_tools()

    assert paths.ios.is_file()
    assert paths.sib.is_file()

