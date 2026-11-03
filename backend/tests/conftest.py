import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session")
def tmpdir_session(tmp_path_factory):
    return tmp_path_factory.mktemp("pollinex")


@pytest.fixture(scope="session")
def client(tmpdir_session):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmpdir_session / 'test.db'}"
    os.environ["UPLOAD_DIR"] = str(tmpdir_session / "uploads")
    os.environ["GALLERY_DIR"] = str(tmpdir_session / "gallery")
    os.environ["JWT_SECRET"] = "test-secret-not-for-production-0123456789abcdef"
    os.environ["WEATHER_API_ENABLED"] = "false"
    os.environ["MAX_UPLOAD_MB"] = "2"
    os.environ["RATE_LIMIT_ENABLED"] = "false"  # enabled explicitly in test_rate_limit
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c


def _register(client, email, password="Str0ngPassword!"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "T"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture(scope="session")
def admin(client):
    return _register(client, "admin@example.com")  # first account -> admin


@pytest.fixture(scope="session")
def user(client, admin):
    return _register(client, "user@example.com")


def jpeg_bytes(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    assert ok
    return buf.tobytes()


@pytest.fixture
def orchard_like_jpeg():
    scene = np.full((540, 720, 3), (70, 110, 55), np.uint8)
    rng = np.random.default_rng(0)
    for _ in range(12):
        x, y = int(rng.integers(30, 690)), int(rng.integers(30, 510))
        cv2.circle(scene, (x, y), int(rng.integers(8, 16)), (245, 243, 238), -1)
        cv2.circle(scene, (x, y), 3, (230, 200, 40), -1)
    return jpeg_bytes(scene)


@pytest.fixture
def closeup_jpeg():
    img = np.full((400, 400, 3), (40, 110, 40), np.uint8)
    for k in range(5):
        a = 2 * np.pi * k / 5
        cv2.ellipse(img, (int(200 + 90 * np.cos(a)), int(200 + 90 * np.sin(a))), (80, 50), np.degrees(a), 0, 360, (220, 30, 50), -1)
    cv2.circle(img, (200, 200), 30, (240, 210, 40), -1)
    return jpeg_bytes(img)


@pytest.fixture
def png_bytes():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 200, 200)).save(b, "PNG")
    return b.getvalue()
