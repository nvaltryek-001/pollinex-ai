#!/usr/bin/env python3
"""Checks that everything POLLINEX AI needs is installed and consistent. Works on Windows, macOS and Linux.

    python scripts/check_dependencies.py            # from the repo root (use the venv's python)

Exit code 0 = all required checks pass; 1 = something required is missing (details printed).
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PY = [  # (import name, pip name)
    ("fastapi", "fastapi"), ("starlette", "starlette"), ("uvicorn", "uvicorn"), ("pydantic", "pydantic"),
    ("email_validator", "email-validator"), ("sqlalchemy", "SQLAlchemy"), ("alembic", "alembic"), ("jwt", "PyJWT"),
    ("multipart", "python-multipart"), ("httpx", "httpx"), ("numpy", "numpy"), ("scipy", "scipy"),
    ("cv2", "opencv-python-headless"), ("skimage", "scikit-image"), ("sklearn", "scikit-learn"), ("joblib", "joblib"),
    ("PIL", "Pillow"), ("reportlab", "reportlab"), ("pytest", "pytest"),
]
OPTIONAL_PY = [("onnxruntime", "onnxruntime (YOLO11 ONNX backend)"), ("psycopg", "psycopg (PostgreSQL)"),
               ("ultralytics", "ultralytics (YOLO11 training only)")]
ok = True


def line(status: str, name: str, detail: str = "") -> None:
    print(f"  [{status:^4}] {name:<34} {detail}")


def fail(name: str, detail: str) -> None:
    global ok
    ok = False
    line("FAIL", name, detail)


print("Python")
if sys.version_info < (3, 11):
    fail("python", f"{sys.version.split()[0]} - need 3.11+")
else:
    line("OK", "python", sys.version.split()[0] + ("  (venv)" if sys.prefix != sys.base_prefix else "  (not in a venv)"))
for mod, pip in REQUIRED_PY:
    try:
        m = importlib.import_module(mod)
        line("OK", pip, str(getattr(m, "__version__", "")))
    except Exception as e:  # noqa: BLE001 - report any import problem
        fail(pip, f"missing ({type(e).__name__}) -> pip install -r backend/requirements.txt")
for mod, label in OPTIONAL_PY:
    try:
        m = importlib.import_module(mod)
        line("OK", label, str(getattr(m, "__version__", "")))
    except Exception:
        line("--", label, "not installed (optional)")

print("Models")
bundle = ROOT / "ai-engine" / "models" / "flower_pixel_hgb.joblib"
if not bundle.exists():
    fail("detector model", f"{bundle} missing - run ai-engine/training/train_detector.py")
else:
    try:
        sys.path.insert(0, str(ROOT / "ai-engine"))
        from pollinex_ai.detector import PixelFlowerDetector  # noqa: E402
        d = PixelFlowerDetector(bundle)
        line("OK", "fallback detector loads", d.version)
    except Exception as e:  # noqa: BLE001
        fail("fallback detector loads", f"{type(e).__name__}: {e} - retrain if scikit-learn differs from 1.9.1")
try:
    sys.path.insert(0, str(ROOT / "ai-engine"))
    from pollinex_ai.detector import load_default_detector  # noqa: E402
    d = load_default_detector()
    if d.backend == "yolo11-onnx":
        line("OK", "default detector (YOLO11 ONNX)", d.version)
    else:
        fail("default detector", f"{d.backend} {d.version} - ai-engine/models/flower_yolo11n.onnx missing, using the pixel fallback")
except Exception as e:  # noqa: BLE001
    fail("default detector (YOLO11 ONNX)", f"{type(e).__name__}: {e} - pip install onnxruntime")
for f in ("embed_mnv3l.onnx",):
    p = ROOT / "ai-engine" / "models" / f
    (line("OK", f + " (species embedding)") if p.exists() else fail(f, "missing - species gallery v2 needs it"))
for f in ("species_gallery.json", "species_gallery.npz"):
    p = ROOT / "ai-engine" / "models" / f
    (line("OK", f) if p.exists() else fail(f, "missing - run ai-engine/training/train_species.py"))

print("Node / frontend")
node, npm = shutil.which("node"), shutil.which("npm") or shutil.which("npm.cmd")
if not node:
    fail("node", "not found - install Node.js 20+")
else:
    v = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    (line("OK", "node", v) if int(v.lstrip("v").split(".")[0]) >= 20 else fail("node", f"{v} - need 20+"))
(line("OK", "npm") if npm else fail("npm", "not found"))
nm = ROOT / "frontend" / "node_modules"
if nm.is_dir():
    pkg = json.loads((ROOT / "frontend" / "package.json").read_text())
    missing = [n for n in {**pkg["dependencies"], **pkg["devDependencies"]} if not (nm / n).exists()]
    (line("OK", "frontend node_modules") if not missing else fail("frontend node_modules", f"missing {missing[:5]} -> npm install"))
else:
    fail("frontend node_modules", "not installed -> cd frontend && npm install")

print("Configuration")
env = ROOT / ".env"
line("OK" if env.exists() else "--", ".env", "present" if env.exists() else "absent (defaults: SQLite + ephemeral JWT secret)")
url = os.environ.get("DATABASE_URL", "")
if not url and env.exists():
    for raw in env.read_text(encoding="utf-8-sig").splitlines():
        if raw.startswith("DATABASE_URL="):
            url = raw.split("=", 1)[1].strip()
if url.startswith("postgresql"):
    try:
        import sqlalchemy as sa
        with sa.create_engine(url, pool_pre_ping=True).connect() as c:
            c.execute(sa.text("select 1"))
        line("OK", "PostgreSQL connection", url.split("@")[-1])
    except Exception as e:  # noqa: BLE001
        fail("PostgreSQL connection", f"{type(e).__name__}: is the server running and the database created?")
else:
    line("OK", "database", "SQLite (backend/pollinex.db)")

print("\nRESULT:", "all required checks passed" if ok else "some required checks FAILED (see above)")
sys.exit(0 if ok else 1)
