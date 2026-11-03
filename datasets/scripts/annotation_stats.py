#!/usr/bin/env python3
"""Annotation statistics, quality checks and CVAT-COCO -> YOLO conversion.

    python datasets/scripts/annotation_stats.py                       # report on every committed dataset
    python datasets/scripts/annotation_stats.py --coco X.json --to-yolo [--review review_log.csv]

Default mode writes datasets/reports/annotation_statistics.{json,md}: per dataset and species the number of images,
box annotations, image-level labels, boxes per image, relative box sizes, and the count of every class in the CVAT
schema (flower_centre, petal, anther, stigma, stamen, pistil, health_issue, stage) - reported as 0 where none exist.

--coco validates a CVAT COCO 1.0 export against datasets/annotation/cvat_labels.json (unknown labels, boxes outside the
image, degenerate polygons, missing / 'uncertain' attributes, images without annotations) and with --to-yolo writes
two YOLO sets next to it - yolo/ (class flower) and yolo_structures/ (anther, stigma, stamen, pistil, petal) - split
70/15/15 by capture session (first folder of file_name, i.e. one CVAT task) so a session never crosses splits.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
REPORTS = ROOT / "datasets" / "reports"
SCHEMA = ROOT / "datasets" / "annotation" / "cvat_labels.json"
STRUCTURES = ["anther", "stigma", "stamen", "pistil", "petal"]
SPECIES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]


def schema_labels() -> list[str]:
    return [lab["name"] for lab in json.loads(SCHEMA.read_text())]


def quantiles(v: list[float]) -> dict:
    if not v:
        return {}
    s = sorted(v)
    q = lambda p: round(s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))], 5)  # noqa: E731
    return {"min": q(0), "p25": q(0.25), "median": q(0.5), "p75": q(0.75), "max": q(1)}


def yolo_stats(name: str, pairs: list[tuple[Path, Path, str, str]]) -> dict:
    """pairs: (image, label, species, split)."""
    per = defaultdict(lambda: {"images": 0, "boxes": 0, "rel_area": [], "split": Counter(), "empty_label_files": 0})
    for _im, lab, sp, split in pairs:
        rows = [r.split() for r in lab.read_text().splitlines() if r.strip()] if lab.exists() else []
        d = per[sp]
        d["images"] += 1
        d["split"][split] += 1
        d["boxes"] += len(rows)
        d["empty_label_files"] += not rows
        d["rel_area"] += [float(r[3]) * float(r[4]) for r in rows]
    out = {}
    for sp, d in per.items():
        out[sp] = {"images": d["images"], "box_annotations": d["boxes"], "split": dict(d["split"]),
                   "boxes_per_image": round(d["boxes"] / max(d["images"], 1), 2), "images_without_boxes": d["empty_label_files"],
                   "relative_box_area": quantiles(d["rel_area"])}
    return {"dataset": name, "annotation_type": "bounding boxes (YOLO, class flower)", "per_species": out}


def committed_report() -> dict:
    datasets = []
    usda = PROC / "usda_fruit_flower"
    if usda.exists():
        recs = json.loads((usda / "records.json").read_text())
        pairs = [(usda / "images" / f"{r['uid']}.jpg", usda / "labels" / f"{r['uid']}.txt", r["species"], r["split"]) for r in recs]
        d = yolo_stats("usda_fruit_flower", pairs)
        d["annotation_type"] = "segmentation masks + boxes derived from mask components"
        datasets.append(d)
    sun = PROC / "tf_flower_detection_sunflower"
    if sun.exists():
        pairs = [(im, sun / s / "labels" / f"{im.stem}.txt", "sunflower", s)
                 for s in ("train", "val", "test") for im in sorted((sun / s / "images").glob("*.jpg"))]
        datasets.append(yolo_stats("tf_flower_detection_sunflower", pairs))
    inat = PROC / "inat_flowering" / "manifest.csv"
    if inat.exists():
        rows = list(csv.DictReader(inat.open(encoding="utf-8")))
        per = defaultdict(lambda: {"images": 0, "split": Counter(), "quality_flags": Counter(), "identification": Counter()})
        for r in rows:
            d = per[r["species"]]
            d["images"] += 1
            d["split"][r["split"]] += 1
            d["identification"][r["identification"]] += 1
            for f in filter(None, r["quality_flags"].split(";")):
                d["quality_flags"][f] += 1
        datasets.append({"dataset": "inat_flowering", "annotation_type": "image-level species label only (no boxes)",
                         "per_species": {k: {"images": v["images"], "image_level_labels": v["images"], "box_annotations": 0,
                                             "split": dict(v["split"]), "identification": dict(v["identification"]),
                                             "quality_flags": dict(v["quality_flags"])} for k, v in per.items()}})
    totals = {sp: {"images": 0, "box_annotations": 0, "image_level_labels": 0} for sp in SPECIES}
    for d in datasets:
        for sp, v in d["per_species"].items():
            if sp in totals:
                totals[sp]["images"] += v["images"]
                totals[sp]["box_annotations"] += v.get("box_annotations", 0)
                totals[sp]["image_level_labels"] += v.get("image_level_labels", v["images"] if v.get("box_annotations") else 0)
    schema_counts = {lab: 0 for lab in schema_labels() if lab != "flower"}
    schema_counts["flower.stage (any)"] = 0
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "datasets": datasets, "species_totals": totals,
            "cvat_schema_class_counts": schema_counts,
            "note": "No CVAT exports exist in the repository yet: every structure / centre / stage / health class has 0 "
                    "annotations. Nothing here is generated or inferred."}


def write_md(rep: dict) -> str:
    L = ["# Annotation statistics", "", f"_Generated {rep['generated_at']} by `datasets/scripts/annotation_stats.py`._", "",
         "| Species | Images | Box annotations | Image-level labels |", "|---|--:|--:|--:|"]
    L += [f"| {sp} | {v['images']} | {v['box_annotations']} | {v['image_level_labels']} |" for sp, v in rep["species_totals"].items()]
    L += ["", "| Schema class (CVAT) | Annotations |", "|---|--:|"]
    L += [f"| {k} | {v} |" for k, v in rep["cvat_schema_class_counts"].items()]
    for d in rep["datasets"]:
        L += ["", f"## {d['dataset']} — {d['annotation_type']}", "", "| Species | Images | Boxes | Split | Details |", "|---|--:|--:|---|---|"]
        for sp, v in d["per_species"].items():
            det = {k: v[k] for k in ("boxes_per_image", "relative_box_area", "quality_flags", "identification") if k in v}
            L.append(f"| {sp} | {v['images']} | {v.get('box_annotations', 0)} | {v['split']} | `{json.dumps(det)}` |")
    L += ["", rep["note"], ""]
    return "\n".join(L)


# ---------------- CVAT COCO export ----------------
def session_of(file_name: str) -> str:
    parts = Path(file_name).parts
    return parts[0] if len(parts) > 1 else "default"


def split_for(session: str) -> str:
    h = int(hashlib.sha1(session.encode()).hexdigest(), 16) % 100
    return "train" if h < 70 else "val" if h < 85 else "test"


def check_coco(coco: dict, review: Path | None = None) -> dict:
    allowed = set(schema_labels())
    cats = {c["id"]: c["name"] for c in coco["categories"]}
    imgs = {i["id"]: i for i in coco["images"]}
    issues, counts, attrs = Counter(), Counter(), defaultdict(Counter)
    per_image = Counter()
    for c in cats.values():
        if c not in allowed:
            issues[f"unknown_label:{c}"] += 1
    for a in coco["annotations"]:
        name = cats.get(a["category_id"], "?")
        counts[name] += 1
        per_image[a["image_id"]] += 1
        im = imgs.get(a["image_id"])
        if im is None:
            issues["annotation_without_image"] += 1
            continue
        x, y, w, h = a.get("bbox", [0, 0, 0, 0])
        if name != "flower_centre" and (w <= 1 or h <= 1):
            issues["degenerate_box"] += 1
        if x < -1 or y < -1 or x + w > im["width"] + 1 or y + h > im["height"] + 1:
            issues["box_outside_image"] += 1
        for seg in a.get("segmentation") or []:
            if isinstance(seg, list) and len(seg) < 6:
                issues["polygon_with_<3_points"] += 1
        for k, v in (a.get("attributes") or {}).items():
            attrs[f"{name}.{k}"][str(v)] += 1
        if name == "flower" and not (a.get("attributes") or {}).get("species"):
            issues["flower_without_species"] += 1
    out = {"images": len(imgs), "images_without_annotations": sum(1 for i in imgs if per_image[i] == 0),
           "annotations_per_class": dict(counts), "attributes": {k: dict(v) for k, v in attrs.items()},
           "issues": dict(issues), "uncertain_species": attrs["flower.species"].get("uncertain", 0),
           "uncertain_stage": attrs["flower.stage"].get("uncertain", 0)}
    if review and review.exists():
        rows = list(csv.DictReader(review.open(encoding="utf-8")))
        agree = sum(r["annotator_a"] == r["annotator_b"] for r in rows)
        out["review"] = {"pairs": len(rows), "agreement": round(agree / len(rows), 4) if rows else None}
    return out


def coco_to_yolo(coco: dict, coco_path: Path) -> dict:
    cats = {c["id"]: c["name"] for c in coco["categories"]}
    by_img = defaultdict(list)
    for a in coco["annotations"]:
        by_img[a["image_id"]].append(a)
    base = coco_path.parent
    written = Counter()
    for kind, classes in (("yolo", ["flower"]), ("yolo_structures", STRUCTURES)):
        root = base / kind
        lists = defaultdict(list)
        for im in coco["images"]:
            split = split_for(session_of(im["file_name"]))
            src = (base / "images" / im["file_name"]).resolve()
            rows = []
            for a in by_img[im["id"]]:
                name = cats.get(a["category_id"])
                if name in classes and a.get("bbox"):
                    x, y, w, h = a["bbox"]
                    rows.append(f"{classes.index(name)} {(x + w / 2) / im['width']:.6f} {(y + h / 2) / im['height']:.6f} "
                                f"{w / im['width']:.6f} {h / im['height']:.6f}")
            if kind == "yolo_structures" and not rows:
                continue  # only images where structures were actually annotated
            lab = root / "labels" / split / (Path(im["file_name"]).with_suffix(".txt").name)
            lab.parent.mkdir(parents=True, exist_ok=True)
            lab.write_text("\n".join(rows) + ("\n" if rows else ""))
            img_link = root / "images" / split / Path(im["file_name"]).name
            img_link.parent.mkdir(parents=True, exist_ok=True)
            if not img_link.exists() and src.exists():
                img_link.symlink_to(src)
            lists[split].append(str(img_link))
            written[f"{kind}:{split}"] += 1
        for s in ("train", "val", "test"):
            (root / f"{s}.txt").write_text("\n".join(lists[s]) + "\n")
        (root / "data.yaml").write_text("train: train.txt\nval: val.txt\ntest: test.txt\nnames:\n" +
                                        "".join(f"  {i}: {c}\n" for i, c in enumerate(classes)))
    return dict(written)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coco", type=Path)
    ap.add_argument("--to-yolo", action="store_true")
    ap.add_argument("--review", type=Path)
    args = ap.parse_args()
    if args.coco:
        coco = json.loads(args.coco.read_text())
        rep = check_coco(coco, args.review)
        if args.to_yolo:
            rep["yolo_written"] = coco_to_yolo(coco, args.coco)
        out = args.coco.with_name("annotation_check.json")
        out.write_text(json.dumps(rep, indent=2))
        print(json.dumps(rep, indent=2))
        return
    rep = committed_report()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "annotation_statistics.json").write_text(json.dumps(rep, indent=2))
    (REPORTS / "annotation_statistics.md").write_text(write_md(rep))
    print(json.dumps(rep["species_totals"], indent=2))


if __name__ == "__main__":
    main()
