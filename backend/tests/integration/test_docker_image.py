"""Builds the Dockerfile at the repo root and checks the resulting image boots and serves the app.

Requires a running Docker daemon. Building the image from scratch takes a few minutes; later runs
reuse the Docker layer cache.
"""

from pathlib import Path

import httpx2
import pytest
from testcontainers.core.config import testcontainers_config
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.wait_strategies import HttpWaitStrategy

REPO_ROOT = Path(__file__).resolve().parents[3]
PORT = 8000

# Ryuk is testcontainers' cleanup sidecar. It needs to bind-mount the Docker socket, which fails on
# Docker Desktop for Mac (the socket lives under ~/.docker/run). The context managers below stop
# and remove the container on exit, so we do not need it.
testcontainers_config.ryuk_disabled = True


@pytest.mark.integration
def test_image_boots_and_serves_app() -> None:
    with (
        DockerImage(path=REPO_ROOT, tag="chess-review:test") as image,
        DockerContainer(str(image))
        .with_exposed_ports(PORT)
        .waiting_for(HttpWaitStrategy(PORT, "/api/health").for_status_code(200).with_startup_timeout(60)) as container,
    ):
        base_url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(PORT)}"
        with httpx2.Client(base_url=base_url, timeout=10) as client:
            health = client.get("/api/health")
            index = client.get("/")
            games = client.get("/api/games")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert index.status_code == 200
    assert "<html" in index.text.lower()
    assert games.status_code == 200
