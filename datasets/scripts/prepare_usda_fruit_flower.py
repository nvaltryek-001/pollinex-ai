#!/usr/bin/env python3
"""Prepare the USDA Multi-species Fruit Flower dataset (Dias, Tabb & Medeiros, 2018; CC BY 4.0).

Steps
-----
1. Locate (or git-clone) the public mirror
   https://github.com/ai-agriculture-circuits-and-systems/multi-species-fruit-flower
2. Keep ONLY images that have both box annotations and a segmentation mask
   (the upstream "train" split for apples contains 100 *unannotated* images - they are excluded,
   never treated as negatives).
3. Resize to a working resolution (longest side <= --max-side), rescale boxes, convert BMP -> JPEG.
4. Build *group-aware, contiguous-block* splits per capture subset so near-identical consecutive
   frames cannot land on both sides of a split (leakage control), then run a perceptual-hash
   near-duplicate audit across splits.
5. Emit YOLO labels, COCO json per split, a split file, quality metrics, and a JSON/Markdown report.

Run from the repository root:
    python datasets/scripts/prepare_usda_fruit_flower.py --src /path/to/multi-species-fruit-flower
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REPO_URL = "https://github.com/ai-agriculture-circuits-and-systems/multi-species-fruit-flower"
DATASET_ID = "usda_fruit_flower"
ROOT = Path(__file__).resolve().parents[2]
SPECIES_DIRS = {"apples": "apple", "peaches": "peach", "pears": "pear"}
SPLIT_FRACTIONS = (0.6, 0.15, 0.25)  # train / val / test per capture group


def capture_group(species_dir: str, stem: str) -> str:
    """Capture subset an image belongs to (different cameras / sessions upstream)."""
    if species_dir == "apples":
        return "apple_A" if stem.startswith("IMG_") else "apple_B"
    if species_dir == "pears":
        return "pear_seq" + stem.split("_")[0]
    return "peach"


def frame_index(stem: str) -> int:
    nums = re.findall(r"\d+", stem)
    return int(nums[-1]) if nums else 0


def mask_name(species_dir: str, stem: str) -> str:
    if species_dir == "apples" and stem.startswith("IMG_"):
        return str(int(stem.split("_")[1]))
    return stem


MIN_INSTANCE_AREA = 9  # px at processed resolution; smaller mask specks are annotation noise


def _iou_hits(a: list, b: list, thr: float = 0.3) -> float:
    if not a or not b:
        return 0.0
    A, B = np.array(a, float), np.array(b, float)
    ix = np.clip(np.minimum(A[:, None, 2], B[None, :, 2]) - np.maximum(A[:, None, 0], B[None, :, 0]), 0, None)
    iy = np.clip(np.minimum(A[:, None, 3], B[None, :, 3]) - np.maximum(A[:, None, 1], B[None, :, 1]), 0, None)
    inter = ix * iy
    aa = (A[:, 2] - A[:, 0]) * (A[:, 3] - A[:, 1])
    bb = (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1])
    iou = inter / np.maximum(aa[:, None] + bb[None, :] - inter, 1e-9)
    return float((iou.max(1) >= thr).mean())


def box_orientation_agreement(upstream: list, mask_boxes: list, w: int, h: int) -> dict:
    """Fraction of upstream boxes overlapping a mask component as-is vs. after a vertical flip."""
    flipped = [[b[0], h - b[3], b[2], h - b[1]] for b in upstream]
    return {"as_is": round(_iou_hits(upstream, mask_boxes), 3), "vflip": round(_iou_hits(flipped, mask_boxes), 3)}


def dhash(img: np.ndarray, size: int = 8) -> int:
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    g = cv2.resize(g, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def ensure_source(src: Path | None) -> Path:
    if src and src.exists():
        return src
    dest = ROOT / "datasets" / "raw" / "multi-species-fruit-flower"
    if not dest.exists():
        print(f"Cloning {REPO_URL} -> {dest} (~6 GB, may take a while)")
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(dest)], check=True,
                       env={"GIT_LFS_SKIP_SMUDGE": "1", **__import__("os").environ})
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=None, help="Path to a local clone of the upstream repo")
    ap.add_argument("--max-side", type=int, default=1600)
    ap.add_argument("--out", type=Path, default=ROOT / "datasets" / "processed" / DATASET_ID)
    args = ap.parse_args()

    src = ensure_source(args.src)
    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out: Path = args.out
    for sub in ("images", "masks", "labels"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    records = []
    excluded = Counter()
    for sdir, species in SPECIES_DIRS.items():
        for jpath in sorted((src / sdir / "json").glob("*.json")):
            stem = jpath.stem
            meta = json.loads(jpath.read_text())
            anns = meta.get("annotations", [])
            mpath = src / sdir / "segmentations" / f"{mask_name(sdir, stem)}.png"
            if not anns:
                excluded["no_box_annotations"] += 1
                continue
            if not mpath.exists():
                excluded["no_mask"] += 1
                continue
            cands = [p for p in (src / sdir / "images").glob(f"{stem}.*")]
            if not cands:
                excluded["image_missing"] += 1
                continue
            ipath = cands[0]
            img = np.array(Image.open(ipath).convert("RGB"))
            mask = np.array(Image.open(mpath)).astype(bool)
            h, w = img.shape[:2]
            if mask.shape != (h, w):  # some JPEGs carry an EXIF rotation; try honouring it
                from PIL import ImageOps
                img = np.array(ImageOps.exif_transpose(Image.open(ipath)).convert("RGB"))
                h, w = img.shape[:2]
            if mask.shape != (h, w):
                excluded["mask_size_mismatch"] += 1
                continue
            scale = min(1.0, args.max_side / max(h, w))
            nh, nw = int(round(h * scale)), int(round(w * scale))
            img_r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
            mask_r = cv2.resize(mask.astype(np.uint8) * 255, (nw, nh), interpolation=cv2.INTER_NEAREST)
            uid = f"{species}_{stem}"
            Image.fromarray(img_r).save(out / "images" / f"{uid}.jpg", quality=92)
            Image.fromarray(mask_r).save(out / "masks" / f"{uid}.png")
            # Authoritative instances: connected components of the upstream mask.
            # (Audit 2026-11: the mirror's per-image JSON boxes are vertically flipped for many images
            #  relative to image+mask - see box_orientation_audit in the report - so they are NOT used as GT.)
            n_cc, _, stats, _ = cv2.connectedComponentsWithStats((mask_r > 0).astype(np.uint8), connectivity=8)
            mask_boxes = [[float(s[0]), float(s[1]), float(s[0] + s[2]), float(s[1] + s[3])]
                          for s in stats[1:] if s[4] >= MIN_INSTANCE_AREA]
            upstream = []
            for a in anns:
                x, y, bw, bh = a["bbox"]
                x1, y1 = max(0.0, x * scale), max(0.0, y * scale)
                x2, y2 = min(nw, (x + bw) * scale), min(nh, (y + bh) * scale)
                if x2 - x1 < 1 or y2 - y1 < 1:
                    excluded["degenerate_upstream_box"] += 1
                    continue
                upstream.append([round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)])
            orient = box_orientation_agreement(upstream, mask_boxes, nw, nh)
            boxes = mask_boxes
            with open(out / "labels" / f"{uid}.txt", "w") as f:  # YOLO format, single class "flower"
                for x1, y1, x2, y2 in boxes:
                    f.write(f"0 {(x1+x2)/2/nw:.6f} {(y1+y2)/2/nh:.6f} {(x2-x1)/nw:.6f} {(y2-y1)/nh:.6f}\n")
            gray = cv2.cvtColor(img_r, cv2.COLOR_RGB2GRAY)
            records.append({
                "uid": uid, "species": species, "source_file": f"{sdir}/images/{ipath.name}",
                "group": capture_group(sdir, stem), "frame": frame_index(stem),
                "orig_w": w, "orig_h": h, "w": nw, "h": nh, "scale": scale, "boxes": boxes,
                "upstream_box_count": len(upstream), "box_orientation_audit": orient,
                "mask_fraction": float((mask_r > 0).mean()),
                "blur_laplacian_var": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                "brightness_mean": float(gray.mean()), "dhash": dhash(img_r),
                "sha1": hashlib.sha1(img_r.tobytes()).hexdigest(),
            })
            print(f"  {uid}: {len(boxes)} boxes")

    # ---- group-aware contiguous block splits ----
    by_group = defaultdict(list)
    for r in records:
        by_group[r["group"]].append(r)
    for g, rs in by_group.items():
        rs.sort(key=lambda r: r["frame"])
        n = len(rs)
        n_tr = max(1, int(round(n * SPLIT_FRACTIONS[0])))
        n_va = max(1, int(round(n * SPLIT_FRACTIONS[1])))
        for i, r in enumerate(rs):
            r["split"] = "train" if i < n_tr else ("val" if i < n_tr + n_va else "test")

    # ---- leakage / duplicate audit ----
    exact_dupes = [k for k, v in Counter(r["sha1"] for r in records).items() if v > 1]
    near_cross = []
    for i, a in enumerate(records):
        for b in records[i + 1:]:
            if a["split"] != b["split"] and hamming(a["dhash"], b["dhash"]) <= 6:
                near_cross.append((a["uid"], a["split"], b["uid"], b["split"], hamming(a["dhash"], b["dhash"])))

    # ---- quality flags ----
    blur = np.array([r["blur_laplacian_var"] for r in records])
    blur_thr = float(np.percentile(blur, 5)) if len(blur) else 0
    low_quality = [r["uid"] for r in records if r["blur_laplacian_var"] < blur_thr or not 30 < r["brightness_mean"] < 230]

    # ---- outputs ----
    splits_dir = ROOT / "datasets" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    split_map = {s: sorted(r["uid"] for r in records if r["split"] == s) for s in ("train", "val", "test")}
    (splits_dir / f"{DATASET_ID}_splits.json").write_text(json.dumps(split_map, indent=2))
    for s, uids in split_map.items():
        coco = {"info": {"description": f"{DATASET_ID} {s} (POLLINEX processed)", "source": REPO_URL,
                         "license": "CC BY 4.0", "doi": "10.15482/USDA.ADC/1423466"},
                "categories": [{"id": 1, "name": "flower"}], "images": [], "annotations": []}
        aid = 1
        for i, r in enumerate([r for r in records if r["split"] == s], start=1):
            coco["images"].append({"id": i, "file_name": f"images/{r['uid']}.jpg", "width": r["w"], "height": r["h"],
                                   "species": r["species"]})
            for x1, y1, x2, y2 in r["boxes"]:
                coco["annotations"].append({"id": aid, "image_id": i, "category_id": 1, "iscrowd": 0,
                                            "bbox": [x1, y1, x2 - x1, y2 - y1], "area": (x2 - x1) * (y2 - y1)})
                aid += 1
        ann_dir = ROOT / "datasets" / "annotations"
        ann_dir.mkdir(parents=True, exist_ok=True)
        (ann_dir / f"{DATASET_ID}_{s}_coco.json").write_text(json.dumps(coco))
    (out / "records.json").write_text(json.dumps(records, indent=1))
    yolo_yaml = out / "data.yaml"
    for s in ("train", "val", "test"):
        (out / f"{s}.txt").write_text("\n".join(f"./images/{u}.jpg" for u in split_map[s]) + "\n")
    yolo_yaml.write_text(f"path: {out.resolve()}\ntrain: train.txt\nval: val.txt\ntest: test.txt\nnames:\n  0: flower\n")

    box_areas = [ (b[2]-b[0])*(b[3]-b[1]) / (r["w"]*r["h"]) for r in records for b in r["boxes"]]
    report = {
        "dataset_id": DATASET_ID, "source": REPO_URL, "upstream_commit": commit,
        "license": "CC BY 4.0", "doi": "10.15482/USDA.ADC/1423466",
        "images_kept": len(records), "excluded": dict(excluded),
        "boxes_total": sum(len(r["boxes"]) for r in records),
        "per_species": {sp: {"images": sum(r["species"] == sp for r in records),
                             "boxes": sum(len(r["boxes"]) for r in records if r["species"] == sp)}
                        for sp in SPECIES_DIRS.values()},
        "per_split": {s: {"images": len(u), "boxes": sum(len(r["boxes"]) for r in records if r["split"] == s),
                          "per_species": dict(Counter(r["species"] for r in records if r["split"] == s))}
                      for s, u in split_map.items()},
        "per_group": {g: len(v) for g, v in by_group.items()},
        "relative_box_area": {"p5": float(np.percentile(box_areas, 5)), "median": float(np.median(box_areas)),
                              "p95": float(np.percentile(box_areas, 95))},
        "exact_duplicates": exact_dupes, "near_duplicates_across_splits_dhash_le6": near_cross,
        "low_quality_flags": low_quality, "blur_threshold_p5": blur_thr,
        "split_policy": "contiguous frame blocks per capture group (60/15/25) - prevents adjacent-frame leakage",
        "ground_truth_policy": f"instances = 8-connected components of upstream masks with area >= {MIN_INSTANCE_AREA}px; "
                               "touching flowers form one instance (cluster)",
        "upstream_box_audit": {
            "upstream_boxes_total": sum(r["upstream_box_count"] for r in records),
            "mean_match_as_is": float(np.mean([r["box_orientation_audit"]["as_is"] for r in records])),
            "mean_match_vflip": float(np.mean([r["box_orientation_audit"]["vflip"] for r in records])),
            "images_where_vflip_matches_better": sum(r["box_orientation_audit"]["vflip"] > r["box_orientation_audit"]["as_is"] for r in records),
            "conclusion": "upstream JSON/CSV boxes are inconsistently oriented (often vertically flipped) relative to "
                          "images and masks; they are excluded from training and evaluation",
        },
    }
    rep_dir = ROOT / "datasets" / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    (rep_dir / f"{DATASET_ID}_report.json").write_text(json.dumps(report, indent=2))
    md = [f"# {DATASET_ID} preparation report", "", f"- Upstream: {REPO_URL} @ `{commit[:12]}`",
          f"- Licence: CC BY 4.0 · DOI 10.15482/USDA.ADC/1423466", f"- Images kept: **{len(records)}**  · boxes: **{report['boxes_total']}**",
          f"- Excluded: {dict(excluded)}", "", "| Split | Images | Boxes | Species mix |", "|---|---|---|---|"]
    for s, v in report["per_split"].items():
        md.append(f"| {s} | {v['images']} | {v['boxes']} | {v['per_species']} |")
    md += ["", "| Species | Images | Boxes |", "|---|---|---|"]
    for sp, v in report["per_species"].items():
        md.append(f"| {sp} | {v['images']} | {v['boxes']} |")
    md += ["", f"- Capture groups: {report['per_group']}",
           f"- Relative box area p5/median/p95: {report['relative_box_area']}",
           f"- Exact duplicates: {len(exact_dupes)} · near-duplicate pairs across splits (dHash<=6): {len(near_cross)}",
           f"- Low-quality flags (blur p5 or extreme brightness): {low_quality}",
           "", "## Ground-truth policy and upstream box audit", "",
           f"- {report['ground_truth_policy']}.",
           f"- Upstream boxes: {report['upstream_box_audit']['upstream_boxes_total']}; mean fraction overlapping a mask "
           f"component as-is = {report['upstream_box_audit']['mean_match_as_is']:.2f}, after vertical flip = "
           f"{report['upstream_box_audit']['mean_match_vflip']:.2f}; flip matches better in "
           f"{report['upstream_box_audit']['images_where_vflip_matches_better']}/{len(records)} images.",
           f"- Conclusion: {report['upstream_box_audit']['conclusion']}.",
           "- Note: annotators labelled the foreground tree only; distant background blossoms are unlabelled, which "
           "penalises detectors that find them (counted as false positives).",
           "", "**Class imbalance:** apple contributes most boxes; peach and pear each come from a single camera "
           "setup, so species is confounded with capture conditions. Species results on this data must not be "
           "read as field-general species recognition."]
    (rep_dir / f"{DATASET_ID}_report.md").write_text("\n".join(md) + "\n")

    with open(ROOT / "datasets" / "processed" / f"{DATASET_ID}_index.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["uid", "species", "split", "group", "boxes", "source_file", "w", "h", "scale"])
        for r in records:
            wr.writerow([r["uid"], r["species"], r["split"], r["group"], len(r["boxes"]), r["source_file"], r["w"], r["h"], r["scale"]])
    print(json.dumps({k: report[k] for k in ("images_kept", "boxes_total", "per_split", "excluded")}, indent=2))
    if near_cross:
        print(f"WARNING: {len(near_cross)} near-duplicate pairs cross splits - see report", file=sys.stderr)


if __name__ == "__main__":
    main()
