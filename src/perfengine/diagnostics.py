from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path


_CONFIGURED = False


def diagnostic_log_path() -> Path:
    override = os.environ.get("PERFENGINE_LOG_PATH")
    if override:
        return Path(override)
    base_dir = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    return base_dir / "PerfEngine" / "logs" / "perfengine.log"


def configure_logging() -> Path:
    global _CONFIGURED
    log_path = diagnostic_log_path()
    if _CONFIGURED:
        return log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
    )
    _CONFIGURED = True
    logging.getLogger(__name__).info("PerfEngine diagnostics logging initialized at %s", log_path)
    return log_path
