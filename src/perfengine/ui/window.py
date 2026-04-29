from __future__ import annotations

from pathlib import Path


def resolve_frontend_entry(root_dir: Path | None = None) -> Path:
    root = root_dir or Path(__file__).resolve().parents[3]
    dist_entry = root / "ui" / "dist" / "index.html"
    if dist_entry.exists():
        return dist_entry
    source_entry = root / "ui" / "index.html"
    if source_entry.exists():
        return source_entry
    raise FileNotFoundError("未找到前端入口页面，请先构建 ui 资源。")


def start_window(api, *, root_dir: Path | None = None, title: str = "Android QA Perf") -> None:
    entry = resolve_frontend_entry(root_dir)
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("未安装 pywebview，请先安装 Python 运行依赖。") from exc

    webview.create_window(title, entry.as_uri(), js_api=api, width=1440, height=960)
    webview.start()
