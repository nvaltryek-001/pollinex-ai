#!/usr/bin/env python3
"""Turn HUMAN-REVIEWED CVAT exports into a species-aware YOLO detection dataset (9 classes).

    python datasets/annotation/import_verified_boxes.py --coco reviewed/*.json [--include-existing] [--out DIR]

Acceptance rules (all enforced; nothing is guessed):
  * Every `flower` box must have the CVAT checkbox attribute `verified` = true. An image with ANY unverified box (for
    example an untouched machine proposal) is rejected as a whole, because a half-reviewed image hides missed flowers.
  * Every box must have a `species` attribute in the nine target species. `other` / `uncertain` boxes are dropped and
    counted.
  * The split of each image is the split of its source photo (datasets/annotation/proposals/proposals_manifest.csv or the
    existing dataset split); it is never re-drawn, so reviewed labels cannot leak between train/val/test.
  * --include-existing adds the original box datasets (USDA apple/peach/pear, TF Flower Detection sunflower), which are
    published ground truth, with their own splits and the leakage exclusion.
Writes <out>/{train,val,test}/{images,labels}, <out>/data.yaml and <out>/import_report.json (counts per species/split,
rejections and their reasons).
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
CLASSES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]
CID = {c: i for i, c in enumerate(CLASSES)}
MANIFEST = ROOT / "datasets" / "annotation" / "proposals" / "proposals_manifest.csv"


def truthy(v) -> bool:
    return v is True or str(v).strip().lower() in ("true", "1", "yes")


def load_splits() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    return {r["file"]: r["split"] for r in csv.DictReader(MANIFEST.open(encoding="utf-8"))}


def find_image(name: str) -> Path | None:
    for cand in (PROC / name, *(PROC / s / name for s in ("inat_flowering", "commons_flowers"))):
        if cand.exists():
            return cand
    return None


def import_coco(files: list[Path], splits: dict[str, str]) -> tuple[list[dict], Counter]:
    """Returns accepted images [{src, split, boxes:[(cls, x1, y1, x2, y2)]}] and rejection counts."""
    out, rej = [], Counter()
    for f in files:
        coco = json.loads(f.read_text())
        cats = {c["id"]: c["name"] for c in coco.get("categories", [])}
        anns = defaultdict(list)
        for a in coco.get("annotations", []):
            if cats.get(a["category_id"]) == "flower":
                anns[a["image_id"]].append(a)
        for im in coco.get("images", []):
            name = im["file_name"]
            boxes, bad = [], False
            for a in anns.get(im["id"], []):
                at = a.get("attributes", {})
                if not truthy(at.get("verified")):
                    bad = True
                    break
                sp = at.get("species")
                if sp not in CID:
                    rej["box_species_other_or_uncertain"] += 1
                    continue
                x, y, w, h = a["bbox"]
                if w <= 1 or h <= 1:
                    rej["box_degenerate"] += 1
                    continue
                boxes.append((CID[sp], x, y, x + w, y + h))
            if bad:
                rej["image_has_unverified_box"] += 1
                continue
            split = splits.get(name) or splits.get(name.split("/", 1)[-1])
            src = find_image(name)
            if split not in ("train", "val", "test"):
                rej["image_split_unknown"] += 1
                continue
            if src is None:
                rej["image_file_missing"] += 1
                continue
            if not boxes:
                rej["image_without_verified_boxes"] += 1  # an empty reviewed image is allowed only as an explicit negative
                continue
            out.append({"src": src, "split": split, "w": im["width"], "h": im["height"], "boxes": boxes})
    return out, rej


def existing() -> list[dict]:
    """Published box datasets: USDA (apple/peach/pear) and TF sunflower, with their own splits; leakage exclusion applied."""
    from PIL import Image

    excl = {ln.split("#")[0].strip() for ln in (PROC / "leakage_exclusions.txt").read_text().splitlines() if ln.split("#")[0].strip()}
    out = []
    usda = PROC / "usda_fruit_flower"
    for split in ("train", "val", "test"):
        for line in (usda / f"{split}.txt").read_text().splitlines():
            if line.strip():
                p = usda / line.strip().removeprefix("./")
                out.append((p, split, CID[p.stem.split("_")[0]]))
    tf = PROC / "tf_flower_detection_sunflower"
    for split in ("train", "val", "test"):
        out += [(p, split, CID["sunflower"]) for p in sorted((tf / split / "images").glob("*.jpg"))]
    res = []
    for p, split, cid in out:
        if split == "test" and p.stem in excl:
            continue
        lab = p.parent.parent / "labels" / f"{p.stem}.txt"
        W, H = Image.open(p).size
        boxes = []
        for r in lab.read_text().splitlines():
            if r.strip():
                _, x, y, w, h = map(float, r.split())
                boxes.append((cid, (x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H))
        res.append({"src": p, "split": split, "w": W, "h": H, "boxes": boxes})
    return res


def write(items: list[dict], out: Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    per = defaultdict(Counter)
    imgs = defaultdict(Counter)
    for k, it in enumerate(items):
        d = out / it["split"]
        (d / "images").mkdir(parents=True, exist_ok=True)
        (d / "labels").mkdir(parents=True, exist_ok=True)
        stem = f"{k:05d}_{it['src'].stem}"
        shutil.copy2(it["src"], d / "images" / f"{stem}{it['src'].suffix}")
        W, H = it["w"], it["h"]
        lines = [f"{c} {((x1 + x2) / 2) / W:.6f} {((y1 + y2) / 2) / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}"
                 for c, x1, y1, x2, y2 in it["boxes"]]
        (d / "labels" / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        for c in {b[0] for b in it["boxes"]}:
            imgs[CLASSES[c]][it["split"]] += 1
        for b in it["boxes"]:
            per[CLASSES[b[0]]][it["split"]] += 1
    (out / "data.yaml").write_text(f"path: {out.as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\n"
                                   f"names: {json.dumps(CLASSES)}\n")
    return {"boxes": {c: dict(per[c]) for c in CLASSES}, "images": {c: dict(imgs[c]) for c in CLASSES}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coco", nargs="*", type=Path, default=[])
    ap.add_argument("--include-existing", action="store_true")
    ap.add_argument("--out", type=Path, default=PROC / "species_boxes_verified")
    args = ap.parse_args()
    items, rej = import_coco(args.coco, load_splits())
    if args.include_existing:
        items += existing()
    counts = write(items, args.out)
    rep = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "classes": CLASSES,
           "coco_files": [str(p) for p in args.coco], "include_existing": args.include_existing,
           "accepted_images": len(items), "rejected": dict(rej), **counts}
    (args.out / "import_report.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps({k: rep[k] for k in ("accepted_images", "rejected", "images")}, indent=1))


if __name__ == "__main__":
    main()
