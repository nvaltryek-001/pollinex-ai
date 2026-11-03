"""Safe image intake: size/format validation, EXIF-orientation fix, metadata stripping, content-addressed storage."""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import get_settings

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "BMP": "image/bmp"}
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # decompression-bomb guard


@dataclass
class StoredImage:
    rgb: np.ndarray
    path: Path
    rel_path: str
    sha256: str
    width: int
    height: int
    size_bytes: int
    content_type: str


def decode_image(data: bytes) -> tuple[Image.Image, str]:
    s = get_settings()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty upload")
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {s.max_upload_mb} MB limit")
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File is not a readable image")
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported image format {fmt}; use JPEG, PNG, WEBP or BMP")
    if min(img.size) < 32:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Image too small (minimum 32 px per side)")
    return ImageOps.exif_transpose(img).convert("RGB"), fmt


def store_image(data: bytes, max_side: int = 2560) -> StoredImage:
    img, _ = decode_image(data)
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)  # re-encode: strips EXIF/GPS metadata
    out = buf.getvalue()
    digest = hashlib.sha256(out).hexdigest()
    rel = f"{digest[:2]}/{digest}.jpg"
    path = get_settings().upload_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(out)
    return StoredImage(np.asarray(img), path, rel, digest, img.width, img.height, len(out), "image/jpeg")


def resolve_upload(rel_path: str) -> Path:
    base = get_settings().upload_dir.resolve()
    p = (base / rel_path).resolve()
    if base not in p.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid path")
    return p
