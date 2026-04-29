from pathlib import Path


def test_dist_index_uses_relative_asset_paths_for_pywebview():
    dist_index = Path("ui/dist/index.html")

    assert dist_index.exists(), "ui/dist/index.html 不存在，请先构建前端资源"

    html = dist_index.read_text(encoding="utf-8")

    assert 'src="./assets/' in html
    assert 'href="./assets/' in html
