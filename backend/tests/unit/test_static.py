from pathlib import Path

from fastapi.testclient import TestClient

from chess_review.api.app import create_app


def test_serves_static_files_with_api_precedence(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>distinctive index content</html>")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "app.js").write_text("console.log('app');")

    client = TestClient(create_app(static_dir=tmp_path))

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert index_response.text == "<html>distinctive index content</html>"

    asset_response = client.get("/assets/app.js")
    assert asset_response.status_code == 200
    assert asset_response.text == "console.log('app');"

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}


def test_no_static_dir_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 404
