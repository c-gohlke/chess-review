from pathlib import Path

from fastapi.testclient import TestClient

from chess_review.api.app import create_app


def test_serves_static_files_with_api_precedence(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>distinctive index content</html>")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "app.js").write_text("console.log('app');")

    client = TestClient(create_app(tmp_path, tmp_path / "db.sqlite3", Path("stockfish")))

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert index_response.text == "<html>distinctive index content</html>"

    asset_response = client.get("/assets/app.js")
    assert asset_response.status_code == 200
    assert asset_response.text == "console.log('app');"

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}


def test_the_page_is_always_revalidated_so_a_new_version_shows(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("")

    client = TestClient(create_app(tmp_path, tmp_path / "db.sqlite3", Path("stockfish")))

    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/index.html").headers["cache-control"] == "no-cache"
    # Built assets carry a content hash in their names, so they may be cached.
    assert "cache-control" not in client.get("/assets/index-abc123.js").headers
