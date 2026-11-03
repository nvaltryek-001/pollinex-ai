#!/usr/bin/env python3
"""Inventory every image under datasets/ (recursively): counts per dataset and species, decode check, exact
duplicates (SHA-1 of file bytes), annotation pairing. Never counts JSON/CSV/TXT/scripts as images.

    python datasets/scripts/audit_datasets.py            # writes datasets/reports/dataset_inventory.{json,md}

Species are inferred only from explicit dataset structure documented in datasets/dataset_sources.json
(e.g. USDA uid prefix "apple_", Oxford folders "<species>/"), never from file contents.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / "datasets"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TARGET = ["hibiscus", "tomato", "sunflower", "apple", "peach", "pear", "strawberry", "brinjal", "chilli"]


def species_of(rel: Path) -> str | None:
    parts = [p.lower() for p in rel.parts]
    name = rel.stem.lower()
    for sp in TARGET:
        if sp in parts or name.startswith(sp + "_") or any(p.endswith("_" + sp) for p in parts):
            return sp
    if "sunflowers" in parts:
        return "sunflower"
    return None


def main() -> None:
    files = [p for p in DS.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXT]
    by_ds: dict[str, dict] = defaultdict(lambda: {"images": 0, "masks": 0, "decoded": 0, "corrupt": [], "by_ext": Counter(),
                                                  "by_species": Counter(), "bytes": 0})
    hashes: dict[str, list[str]] = defaultdict(list)
    for p in sorted(files):
        rel = p.relative_to(DS)
        # dataset = first two path components below raw/ or processed/, else first component
        parts = rel.parts
        ds = "/".join(parts[:2]) if parts[0] in ("raw", "processed") and len(parts) > 2 else parts[0]
        kind = "masks" if "masks" in parts or "segmentations" in parts else ("reports" if parts[0] == "reports" else "images")
        rec = by_ds[ds]
        rec["bytes"] += p.stat().st_size
        rec["by_ext"][p.suffix.lower()] += 1
        try:
            with Image.open(p) as im:
                im.load()
            rec["decoded"] += 1
        except (UnidentifiedImageError, OSError) as e:
            rec["corrupt"].append(f"{rel}: {type(e).__name__}")
        if kind == "masks":
            rec["masks"] += 1
            continue
        if kind == "reports":
            rec.setdefault("report_figures", 0)
            rec["report_figures"] = rec.get("report_figures", 0) + 1
            continue
        rec["images"] += 1
        sp = species_of(rel)
        rec["by_species"][sp or "unspecified"] += 1
        hashes[hashlib.sha1(p.read_bytes()).hexdigest()].append(str(rel))

    # annotation pairing for YOLO-style datasets (images/<stem>.* <-> labels/<stem>.txt)
    pairing = {}
    for img_dir in DS.rglob("images"):
        if not img_dir.is_dir():
            continue
        lab_dir = img_dir.parent / "labels"
        imgs = {p.stem for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXT}
        if lab_dir.is_dir():
            labs = {p.stem for p in lab_dir.glob("*.txt")}
            pairing[str(img_dir.relative_to(DS))] = {"images": len(imgs), "label_files": len(labs),
                                                      "images_without_labels": len(imgs - labs),
                                                      "labels_without_images": len(labs - imgs)}
    dups = {h: v for h, v in hashes.items() if len(v) > 1}
    empty_dirs = sorted(str(d.relative_to(DS)) for d in DS.rglob("*")
                        if d.is_dir() and not any(x.name != ".gitkeep" for x in d.iterdir()))
    species_total = Counter()
    for ds, r in by_ds.items():
        if not ds.startswith("reports"):
            species_total.update({k: v for k, v in r["by_species"].items()})
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Counts only image files (jpg/jpeg/png/webp/bmp) physically present under datasets/. "
                "Report figures and segmentation masks are counted separately and are not dataset images.",
        "total_dataset_images": sum(r["images"] for ds, r in by_ds.items()),
        "species_image_counts": {sp: species_total.get(sp, 0) for sp in TARGET} | {"unspecified": species_total.get("unspecified", 0)},
        "datasets": {ds: {**{k: v for k, v in r.items() if k not in ("by_ext", "by_species")},
                          "by_ext": dict(r["by_ext"]), "by_species": dict(r["by_species"]),
                          "megabytes": round(r["bytes"] / 1e6, 1)} for ds, r in sorted(by_ds.items())},
        "yolo_pairing": pairing,
        "exact_duplicate_groups": len(dups), "exact_duplicates_examples": list(dups.values())[:10],
        "empty_dirs": empty_dirs,
    }
    rep = DS / "reports"
    rep.mkdir(exist_ok=True)
    (rep / "dataset_inventory.json").write_text(json.dumps(out, indent=2))
    md = ["# Dataset inventory (actual files)", "", f"_Generated {out['generated_at']} by `datasets/scripts/audit_datasets.py`._", "",
          f"**Dataset images present: {out['total_dataset_images']}** (masks and report figures excluded).", "",
          "| Species | Images present |", "|---|---|"]
    md += [f"| {sp} | {n} |" for sp, n in out["species_image_counts"].items()]
    md += ["", "| Location | Images | Masks | Decoded OK | Corrupt | MB | Formats |", "|---|---|---|---|---|---|---|"]
    for ds, r in out["datasets"].items():
        md.append(f"| `{ds}` | {r['images']} | {r['masks']} | {r['decoded']} | {len(r['corrupt'])} | {r['megabytes']} | {r['by_ext']} |")
    md += ["", f"Exact duplicate groups: **{out['exact_duplicate_groups']}**", "", "YOLO image/label pairing:", ""]
    md += [f"- `{k}`: {v}" for k, v in pairing.items()] or ["- none"]
    md += ["", f"Empty directories: {empty_dirs or 'none'}"]
    (rep / "dataset_inventory.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
