from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from perfengine.app.errors import OperatorError


@dataclass(frozen=True, slots=True)
class IOSToolPaths:
    ios: Path
    sib: Path


class IOSTooling:
    def __init__(self, root_dir: Path | str | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir is not None else self._default_root_dir()

    @staticmethod
    def _default_root_dir() -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def assets_dir(self) -> Path:
        return self.root_dir / "assets" / "ios"

    def paths(self) -> IOSToolPaths:
        return IOSToolPaths(
            ios=self.assets_dir / "ios.exe",
            sib=self.assets_dir / "sib.exe",
        )

    def require_tools(self) -> IOSToolPaths:
        paths = self.paths()
        missing = [path.name for path in (paths.ios, paths.sib) if not path.is_file()]
        if missing:
            raise OperatorError(
                code="ios_tools_missing",
                message=(
                    "iOS bundled tools are missing. Reinstall the tool package or "
                    f"restore assets/ios/{', '.join(missing)}."
                ),
            )
        return paths

