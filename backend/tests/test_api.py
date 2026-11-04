"""API, database, upload and inference integration tests."""
from datetime import datetime, timezone

API = "/api/v1"


# ---------------- system ----------------
def test_health_and_openapi(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200 and r.json()["checks"]["database"] == "ok"
    spec = client.get("/openapi.json").json()
    assert "/api/v1/scans" in spec["paths"] and "/api/v1/simulations/{sim_id}/replay" in spec["paths"]


# ---------------- auth ----------------
def test_first_user_is_admin_then_users(admin, user):
    assert admin[1]["role"] == "admin" and user[1]["role"] == "user"


def test_register_rejects_weak_and_duplicate(client, admin):
    assert client.post(f"{API}/auth/register", json={"email": "w@example.com", "password": "short"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={"email": "w@example.com", "password": "alllowercase123"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={"email": "admin@example.com", "password": "Str0ngPassword!"}).status_code == 409


def test_login_logout_revokes_token(client, admin):
    r = client.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "Str0ngPassword!"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(f"{API}/auth/me", headers=h).status_code == 200
    assert client.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "wrong"}).status_code == 401
    # logout bumps token_version -> every older token (incl. the session fixture's) is revoked; log in again
    assert client.post(f"{API}/auth/logout", headers=h).status_code == 204
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    r = client.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "Str0ngPassword!"})
    admin[0]["Authorization"] = f"Bearer {r.json()['access_token']}"


def test_requires_auth(client):
    assert client.get(f"{API}/scans").status_code == 401
    assert client.get(f"{API}/scans", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_role_enforcement(client, user, admin):
    assert client.get(f"{API}/admin/users", headers=user[0]).status_code == 403
    assert client.get(f"{API}/admin/users", headers=admin[0]).status_code == 200
    assert client.get(f"{API}/analytics/dashboard?scope=all", headers=user[0]).status_code == 403


# ---------------- uploads + inference + DB ----------------
def test_scan_upload_runs_real_inference_and_persists(client, user, orchard_like_jpeg):
    r = client.post(f"{API}/scans", headers=user[0], files={"file": ("o.jpg", orchard_like_jpeg, "image/jpeg")},
                    data={"mode": "auto"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["flower_count"] >= 0 and d["latency_ms"] > 0
    assert d["detection_method"] in {"trained_model", "closeup_fallback"}
    for f in d["flowers"]:
        assert f["stage"]["method"] == "heuristic"
        assert f["readiness"]["method"] == "rule_engine"
        assert f["structure"]["structure_detection_available"] is False
    sid = d["id"]
    assert client.get(f"{API}/scans/{sid}", headers=user[0]).json()["id"] == sid
    img = client.get(f"{API}/scans/{sid}/image", headers=user[0])
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    hist = client.get(f"{API}/scans?page=1&page_size=5", headers=user[0]).json()
    assert hist["total"] >= 1 and hist["items"][0]["id"] == sid


def test_scan_closeup_with_species_hint(client, user, closeup_jpeg):
    r = client.post(f"{API}/scans", headers=user[0], files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")},
                    data={"mode": "closeup", "species_hint": "hibiscus"})
    assert r.status_code == 201, r.text
    f = r.json()["flowers"][0]
    assert f["species"]["species"] == "hibiscus" and f["species"]["method"] == "user_declared"
    assert f["readiness"]["species"] == "hibiscus" and f["readiness"]["strategy"]["mechanism"] == "contact_transfer"


def test_scan_isolation_between_users(client, user, admin, closeup_jpeg):
    sid = client.post(f"{API}/scans", headers=user[0], files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")},
                      data={"mode": "closeup"}).json()["id"]
    assert client.get(f"{API}/scans/{sid}", headers=admin[0]).status_code == 404


def test_invalid_uploads(client, user):
    h = user[0]
    assert client.post(f"{API}/scans", headers=h, files={"file": ("e.jpg", b"", "image/jpeg")}).status_code == 400
    assert client.post(f"{API}/scans", headers=h, files={"file": ("t.txt", b"not an image", "text/plain")}).status_code == 415
    big = b"\xff\xd8" + b"0" * (3 * 1024 * 1024)
    assert client.post(f"{API}/scans", headers=h, files={"file": ("b.jpg", big, "image/jpeg")}).status_code == 413
    import io
    from PIL import Image
    tiny = io.BytesIO()
    Image.new("RGB", (10, 10)).save(tiny, "PNG")
    assert client.post(f"{API}/scans", headers=h, files={"file": ("s.png", tiny.getvalue(), "image/png")}).status_code == 422
    gif = io.BytesIO()
    Image.new("RGB", (64, 64)).save(gif, "GIF")
    assert client.post(f"{API}/scans", headers=h, files={"file": ("g.gif", gif.getvalue(), "image/gif")}).status_code == 415


def test_unknown_species_hint_rejected(client, user, closeup_jpeg):
    r = client.post(f"{API}/scans", headers=user[0], files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")},
                    data={"species_hint": "dragonfruit"})
    assert r.status_code == 422


def test_live_frame_endpoint(client, user, orchard_like_jpeg):
    r = client.post(f"{API}/scans/live/frame", headers=user[0], files={"file": ("f.jpg", orchard_like_jpeg, "image/jpeg")})
    assert r.status_code == 200 and "detections" in r.json() and r.json()["latency_ms"] > 0


def test_live_websocket(client, user, orchard_like_jpeg):
    import base64
    token = user[0]["Authorization"].split()[1]
    with client.websocket_connect(f"{API}/scans/live/ws") as ws:
        ws.send_json({"token": token})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"frame_id": 1, "image": base64.b64encode(orchard_like_jpeg).decode()})
        msg = ws.receive_json()
        assert msg["type"] == "result" and msg["frame_id"] == 1
        ws.send_json({"frame_id": 2, "image": "!!notbase64"})
        assert ws.receive_json()["type"] == "error"


def test_ai_module_endpoints(client, user, closeup_jpeg):
    h, f = user[0], {"file": ("c.jpg", closeup_jpeg, "image/jpeg")}
    assert client.post(f"{API}/ai/detect", headers=h, files=f).status_code == 200
    for ep in ("classify-species", "structure", "maturity", "health"):
        assert client.post(f"{API}/ai/{ep}", headers=h, files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")}).status_code == 200
    r = client.post(f"{API}/ai/readiness", headers=h, json={"species_id": "tomato", "stage": "fully_open", "temperature_c": 36})
    assert r.status_code == 200 and r.json()["category"] == "likely_ready"
    assert any(x["effect"] == "unfavourable" for x in r.json()["factors"])
    sp = client.get(f"{API}/ai/species", headers=h).json()
    assert len(sp["species"]) >= 9


def test_reference_upload_requires_researcher(client, user, admin, closeup_jpeg):
    f = {"file": ("c.jpg", closeup_jpeg, "image/jpeg")}
    assert client.post(f"{API}/ai/species/hibiscus/references", headers=user[0], files=f).status_code == 403
    r = client.post(f"{API}/ai/species/hibiscus/references", headers=admin[0], files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")})
    assert r.status_code == 200 and r.json()["gallery_counts"]["hibiscus"] >= 1


# ---------------- simulations ----------------
def test_simulation_lifecycle(client, user):
    h = user[0]
    r = client.post(f"{API}/simulations", headers=h, json={"species_id": "tomato", "overrides": {"vibration_hz": 160, "seed": 5}})
    assert r.status_code == 201 and r.json()["status"] == "created"
    sid = r.json()["id"]
    assert client.get(f"{API}/simulations/{sid}/replay", headers=h).status_code == 409
    ex = client.post(f"{API}/simulations/{sid}/execute", headers=h).json()
    assert ex["status"] == "completed" and 0 <= ex["result_summary"]["simulated_transfer_efficiency"] <= 1
    rep = client.get(f"{API}/simulations/{sid}/replay", headers=h).json()
    assert rep["frames"] and "not evidence" in rep["disclaimer"].lower()
    assert client.post(f"{API}/simulations", headers=h, json={"species_id": "tomato", "overrides": {"evil": 1}}).status_code == 422
    sw = client.post(f"{API}/simulations/sweep", headers=h, json={"species_id": "apple", "parameter": "effector_offset_mm",
                                                                  "values": [[0, 0], [3, 0]]})
    assert sw.status_code == 200 and len(sw.json()["rows"]) == 2


# ---------------- records, analytics, reports ----------------
def test_field_plant_environment_pollination(client, user):
    h = user[0]
    fid = client.post(f"{API}/fields", headers=h, json={"name": "Block A", "latitude": 12.97, "longitude": 77.59}).json()["id"]
    pid = client.post(f"{API}/plants", headers=h, json={"label": "T-01", "field_id": fid, "species_id": "tomato"}).json()["id"]
    assert client.post(f"{API}/plants", headers=h, json={"label": "X", "species_id": "nope"}).status_code == 422
    env = client.post(f"{API}/environment", headers=h, json={"observed_at": datetime.now(timezone.utc).isoformat(),
                                                             "temperature_c": 27, "relative_humidity_pct": 70, "field_id": fid})
    assert env.status_code == 201 and env.json()["source"] == "manual"
    assert client.post(f"{API}/environment", headers=h, json={"observed_at": "2026-01-01T00:00:00Z", "relative_humidity_pct": 150}).status_code == 422
    a = client.get(f"{API}/environment/{env.json()['id']}/assessment?species_id=tomato", headers=h)
    assert a.status_code == 200
    # weather integration disabled in tests -> explicit 503, never invented readings
    assert client.post(f"{API}/environment/fetch", headers=h, json={"latitude": 12.9, "longitude": 77.6}).status_code == 503
    pr = client.post(f"{API}/pollination-records", headers=h, json={"method": "vibration", "plant_id": pid, "species_id": "tomato",
                                                                    "performed_at": datetime.now(timezone.utc).isoformat()})
    assert pr.status_code == 201


def test_dashboard_reflects_database(client, user):
    d = client.get(f"{API}/analytics/dashboard", headers=user[0]).json()
    t = d["totals"]
    assert t["scanned_images"] >= 3 and t["simulation_runs"] >= 1 and t["pollination_records"] >= 1
    assert "database records" in d["provenance"]


def test_reports_download(client, user):
    csv = client.get(f"{API}/reports/scans.csv", headers=user[0])
    assert csv.status_code == 200 and csv.text.startswith("scan_id,")
    pdf = client.get(f"{API}/reports/summary.pdf", headers=user[0])
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_admin_user_management(client, admin, user):
    uid = user[1]["id"]
    r = client.patch(f"{API}/admin/users/{uid}", headers=admin[0], json={"role": "researcher"})
    assert r.status_code == 200 and r.json()["role"] == "researcher"
    assert client.patch(f"{API}/admin/users/{admin[1]['id']}", headers=admin[0], json={"role": "user"}).status_code == 409
    assert client.get(f"{API}/admin/activity", headers=admin[0]).json()["total"] > 0
    assert client.get(f"{API}/datasets", headers=admin[0]).status_code == 200
    assert len(client.get(f"{API}/research/references", headers=admin[0]).json()) >= 6


def test_manual_species_correction_reruns_readiness(client, closeup_jpeg):
    # own account: the shared `user` fixture's token is revoked by the role change in test_admin_user_management
    r = client.post(f"{API}/auth/register", json={"email": "corrector@example.com", "password": "Str0ngPassword!"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    resp = client.post(f"{API}/scans", headers=h, files={"file": ("c.jpg", closeup_jpeg, "image/jpeg")}, data={"mode": "closeup"})
    assert resp.status_code == 201, resp.text
    scan = resp.json()
    original = scan["flowers"][0]["species"]["species"]
    r = client.patch(f"{API}/scans/{scan['id']}/flowers/0/species", headers=h, json={"species_id": "tomato"})
    assert r.status_code == 200, r.text
    f = r.json()["flowers"][0]
    assert f["species"]["species"] == "tomato" and f["species"]["method"] == "user_corrected"
    assert f["species"]["original_prediction"] == original
    assert f["readiness"]["species"] == "tomato" and f["readiness"]["strategy"]["mechanism"] == "vibration"
    assert r.json()["summary"]["species_counts"] == {"tomato": 1}
    assert client.patch(f"{API}/scans/{scan['id']}/flowers/0/species", headers=h, json={"species_id": "cactus"}).status_code == 422
    assert client.patch(f"{API}/scans/{scan['id']}/flowers/99/species", headers=h, json={"species_id": "apple"}).status_code == 404


def test_standard_user_blocked_from_all_admin_endpoints(client):
    r = client.post(f"{API}/auth/register", json={"email": "plain@example.com", "password": "Str0ngPassword!"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert r.json()["user"]["role"] == "user"
    for method, path in [("get", "/admin/users"), ("patch", "/admin/users/1"), ("get", "/admin/activity"),
                         ("get", "/admin/models"), ("post", "/admin/models/reload"),
                         ("get", "/analytics/dashboard?scope=all"), ("get", "/analytics/species?scope=all")]:
        kw = {"json": {"role": "user"}} if method == "patch" else {}
        assert getattr(client, method)(f"{API}{path}", headers=h, **kw).status_code == 403, path


def test_rate_limit(client, monkeypatch):
    from app.services import ratelimit
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    ratelimit.reset()
    codes = [client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "x"}).status_code
             for _ in range(22)]
    assert codes[:20] == [401] * 20 and codes[-1] == 429
    ratelimit.reset()


def test_backend_startup_seeds_reference_data(client):
    h = client.get(f"{API}/health").json()
    assert h["status"] == "ok" and h["model"]["detector_backend"]


def test_detector_switch_is_admin_only_and_safe(client, admin):
    # own account: the shared `user` token is revoked by the role change in test_admin_user_management
    reg = client.post(f"{API}/auth/register", json={"email": "detector-switch@example.com", "password": "Str0ngPassword!", "full_name": "D"})
    user = ({"Authorization": f"Bearer {reg.json()['access_token']}"}, reg.json()["user"])
    r = client.get(f"{API}/admin/models", headers=admin[0])
    assert r.status_code == 200 and r.json()["detector_choice"] in {"auto", "yolo11", "pixel"}
    avail = r.json()["available_detectors"]
    assert client.post(f"{API}/admin/models/detector", headers=user[0], json={"detector": "pixel"}).status_code == 403
    assert client.post(f"{API}/admin/models/detector", headers=admin[0], json={"detector": "bogus"}).status_code == 422
    r = client.post(f"{API}/admin/models/detector", headers=admin[0], json={"detector": "pixel"})
    assert r.status_code == 200 and r.json()["active"]["detector_backend"].startswith("pixel")
    r = client.post(f"{API}/admin/models/detector", headers=admin[0], json={"detector": "yolo11"})
    if avail["yolo11"]:
        assert r.status_code == 200 and r.json()["active"]["detector_backend"] == "yolo11-onnx"
    else:
        assert r.status_code == 409  # missing model: previous detector stays active
    assert client.post(f"{API}/admin/models/detector", headers=admin[0], json={"detector": "auto"}).status_code == 200


def test_hosting_postgres_urls_use_psycopg3(monkeypatch):
    from app.config import Settings
    for url in ("postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db"):
        monkeypatch.setenv("DATABASE_URL", url)
        assert Settings().ensure().database_url == "postgresql+psycopg://u:p@h:5432/db"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    assert Settings().ensure().database_url == "postgresql+psycopg://u:p@h/db"


def test_single_service_serves_spa_with_fallback(client, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>pollinex spa</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    c = TestClient(create_app())  # no lifespan: routing only
    assert "pollinex spa" in c.get("/app/scanner").text
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/api/v1/does-not-exist").status_code == 404
    assert c.get("/../etc/passwd").status_code in (200, 404) and "root:" not in c.get("/../etc/passwd").text
