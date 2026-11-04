#!/usr/bin/env python3
"""Machine-readable per-species dataset inventory built from the files on disk.

    python datasets/scripts/dataset_quality_audit.py     # decode / duplicate / leakage audit (run first)
    python datasets/scripts/build_species_inventory.py

Writes datasets/reports/species_inventory.json and species_inventory.md. Counts come from the image files, the YOLO label
files and the quality audit; external dataset status comes from datasets/dataset_sources.json. Nothing is estimated.
Image-level (recognition) photos are never counted as detection data.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
REP = ROOT / "datasets" / "reports"
SPECIES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]


def yolo_boxes() -> tuple[dict, dict]:
    """Box and box-image counts per species and split, from the YOLO label files actually committed."""
    boxes, imgs = defaultdict(Counter), defaultdict(Counter)
    usda = PROC / "usda_fruit_flower"
    for split in ("train", "val", "test"):
        for line in (usda / f"{split}.txt").read_text().splitlines():
            if not line.strip():
                continue
            stem = Path(line.strip()).stem
            n = sum(1 for r in (usda / "labels" / f"{stem}.txt").read_text().splitlines() if r.strip())
            sp = stem.split("_")[0]
            boxes[sp][split] += n
            imgs[sp][split] += 1
    tf = PROC / "tf_flower_detection_sunflower"
    for split in ("train", "val", "test"):
        for lab in (tf / split / "labels").glob("*.txt"):
            boxes["sunflower"][split] += sum(1 for r in lab.read_text().splitlines() if r.strip())
            imgs["sunflower"][split] += 1
    return boxes, imgs


def main():
    qa = json.loads((REP / "dataset_quality_audit.json").read_text())
    reg = json.loads((ROOT / "datasets" / "dataset_sources.json").read_text())
    boxes, box_imgs = yolo_boxes()
    leak = [ln.split("#")[0].strip() for ln in (PROC / "leakage_exclusions.txt").read_text().splitlines() if ln.split("#")[0].strip()]
    species = {}
    for sp in SPECIES:
        q = qa["per_species"].get(sp, {})
        species[sp] = {
            "images_total": q.get("images", 0),
            "classification_labelled_images": q.get("recognition", 0),
            "detection_images_with_boxes": int(sum(box_imgs[sp].values())),
            "detection_boxes": int(sum(boxes[sp].values())),
            "detection_boxes_by_split": dict(boxes[sp]),
            "images_by_split": q.get("splits", {}),
            "images_by_source": q.get("sources", {}),
            "licences": q.get("licences", {}),
            "downloaded": q.get("images", 0) > 0,
        }
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_files": ["datasets/reports/dataset_quality_audit.json", "datasets/dataset_sources.json",
                         "datasets/processed/*/labels"],
        "totals": {"images": qa["images_checked"], "decoded_ok": qa["decoded_ok"], "corrupt": qa["corrupt"],
                   "exact_duplicate_groups": qa["exact_duplicate_groups"], "near_duplicate_pairs": qa["near_duplicate_pairs"],
                   "cross_split_leakage_pairs": qa["cross_split_leakage_pairs"], "leakage_excluded_from_test": leak,
                   "smaller_than_160px": qa["smaller_than_160px"]},
        "rule": "Only USDA and TF Flower Detection images carry boxes. iNaturalist and Commons photos are image-level species "
                "labels and are never used as detection data.",
        "species": species,
        "external_datasets": {d["id"]: {"name": d.get("name"), "status": d.get("status"),
                                        "note": d.get("notes") or d.get("reason") or ""} for d in reg["datasets"]},
        "status_legend": reg.get("status_legend"),
    }
    (REP / "species_inventory.json").write_text(json.dumps(out, indent=2))
    L = ["# Species dataset inventory", "", f"Generated {out['generated_at']} by `datasets/scripts/build_species_inventory.py` "
         "from the files on disk.", "",
         f"Totals: {out['totals']['images']} images, {out['totals']['decoded_ok']} decode, {out['totals']['corrupt']} corrupt, "
         f"{out['totals']['exact_duplicate_groups']} exact-duplicate groups, {out['totals']['near_duplicate_pairs']} near-duplicate pairs, "
         f"{out['totals']['cross_split_leakage_pairs']} cross-split leakage pair (excluded from test: {', '.join(leak)}).", "",
         "| Species | Images | train / val / test | Classification labels | Images with boxes | Boxes | Sources |",
         "|---|--:|---|--:|--:|--:|---|"]
    for sp, v in species.items():
        s = v["images_by_split"]
        L.append(f"| {sp} | {v['images_total']} | {s.get('train', 0)} / {s.get('val', 0)} / {s.get('test', 0)} | "
                 f"{v['classification_labelled_images']} | {v['detection_images_with_boxes']} | {v['detection_boxes']} | "
                 + ", ".join(f"{k} {n}" for k, n in v["images_by_source"].items()) + " |")
    L += ["", out["rule"], "", "## External datasets", "", "| Dataset | Status | Note |", "|---|---|---|"]
    for k, v in out["external_datasets"].items():
        L.append(f"| {v['name']} | {v['status']} | {v['note'][:160]} |")
    (REP / "species_inventory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[6:17]))


if __name__ == "__main__":
    main()
