#!/usr/bin/env python3
"""Cross-source dataset quality audit: integrity, duplicates, split leakage, suitability, licences, suspected label noise.

    python datasets/scripts/dataset_quality_audit.py

Covers every committed image set: usda_fruit_flower, tf_flower_detection_sunflower, inat_flowering, commons_flowers.
Writes datasets/reports/dataset_quality_audit.{json,md}:
  * integrity: decode errors, tiny images
  * duplicates: exact (SHA-1 of pixels) and near (64-bit dHash, Hamming <= 4) - across ALL sources
  * leakage: duplicate / near-duplicate pairs whose members sit in different splits (train/val/test), within or across
    sources - the most important check before reporting any test metric
  * suitability per image: species recognition (has species label), flower detection (has boxes), close-up structure
    analysis (has boxes AND the largest box covers >= 15 % of the image with min side >= 160 px - i.e. a flower large enough
    that anthers/stigma could be annotated; NOT a claim that they are visible)
  * licences per species and source (from each set's manifest / licence file)
  * suspected label noise: image-level photos whose 5 nearest neighbours (ImageNet MobileNetV3 embedding, other images of
    the same pool, leave-one-out) all belong to ONE other species with cosine >= 0.80 - a review list, not a correction.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
REPORTS = ROOT / "datasets" / "reports"
sys.path.insert(0, str(ROOT / "ai-engine"))


def dhash(img: Image.Image) -> int:
    g = np.asarray(img.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def collect() -> list[dict]:
    items = []
    usda = PROC / "usda_fruit_flower"
    if usda.exists():
        for r in json.loads((usda / "records.json").read_text()):
            items.append({"source": "usda_fruit_flower", "path": usda / "images" / f"{r['uid']}.jpg", "species": r["species"],
                          "split": r["split"], "label": usda / "labels" / f"{r['uid']}.txt", "licence": "CC BY 4.0"})
    sun = PROC / "tf_flower_detection_sunflower"
    for s in ("train", "val", "test"):
        for p in sorted((sun / s / "images").glob("*.jpg")):
            items.append({"source": "tf_flower_detection_sunflower", "path": p, "species": "sunflower", "split": s,
                          "label": sun / s / "labels" / f"{p.stem}.txt", "licence": "CC BY 4.0 (boxes) / CC-BY Flickr (image)"})
    for name in ("inat_flowering", "commons_flowers"):
        man = PROC / name / "manifest.csv"
        if man.exists():
            for r in csv.DictReader(man.open(encoding="utf-8")):
                items.append({"source": name, "path": PROC / name / r["file"], "species": r["species"], "split": r["split"],
                              "label": None, "licence": r["licence"]})
    return items


def main():
    items = collect()
    corrupt, tiny = [], []
    for it in items:
        try:
            im = Image.open(it["path"])
            im.load()
            im = im.convert("RGB")
        except Exception as e:  # noqa: BLE001
            corrupt.append({"file": str(it["path"].relative_to(ROOT)), "error": str(e)[:120]})
            it["ok"] = False
            continue
        it["ok"] = True
        it["w"], it["h"] = im.size
        if min(im.size) < 160:
            tiny.append(str(it["path"].relative_to(ROOT)))
        it["sha"] = hashlib.sha1(np.asarray(im).tobytes()).hexdigest()
        it["dh"] = dhash(im)
        boxes = []
        if it["label"] is not None and it["label"].exists():
            boxes = [list(map(float, ln.split()[1:])) for ln in it["label"].read_text().splitlines() if ln.strip()]
        it["n_boxes"] = len(boxes)
        big = max((w * h for _, _, w, h in boxes), default=0.0)
        min_side = max((min(w * it["w"], h * it["h"]) for _, _, w, h in boxes), default=0.0)
        it["suit"] = {"recognition": True, "detection": len(boxes) > 0,
                      "closeup_structure_candidate": bool(boxes) and big >= 0.15 and min_side >= 160}
    ok = [it for it in items if it.get("ok")]
    # duplicates + leakage
    by_sha = defaultdict(list)
    for it in ok:
        by_sha[it["sha"]].append(it)
    exact = [g for g in by_sha.values() if len(g) > 1]
    near = []
    H = np.array([it["dh"] for it in ok], dtype=np.uint64)
    for i in range(len(ok)):
        x = np.bitwise_xor(H[i + 1:], H[i])
        dist = np.array([bin(int(v)).count("1") for v in x]) if len(x) else np.array([])
        for j in np.where(dist <= 4)[0]:
            a, b = ok[i], ok[i + 1 + int(j)]
            if a["sha"] != b["sha"]:
                near.append((a, b, int(dist[j])))
    excl_file = PROC / "leakage_exclusions.txt"
    excluded = {ln.split("#")[0].strip() for ln in excl_file.read_text().splitlines()} if excl_file.exists() else set()
    leaks = []
    for a, b, d in [(g[0], g[k], 0) for g in exact for k in range(1, len(g))] + near:
        if a["split"] != b["split"]:
            leaks.append({"a": str(a["path"].relative_to(ROOT)), "a_split": a["split"], "b": str(b["path"].relative_to(ROOT)),
                          "b_split": b["split"], "hamming": d, "same_species": a["species"] == b["species"],
                          "resolved_by_test_exclusion": a["path"].stem in excluded or b["path"].stem in excluded})
    # suitability + licences
    per = defaultdict(lambda: {"images": 0, "recognition": 0, "detection": 0, "closeup_structure_candidate": 0,
                               "sources": Counter(), "splits": Counter(), "licences": Counter()})
    for it in ok:
        d = per[it["species"]]
        d["images"] += 1
        d["sources"][it["source"]] += 1
        d["splits"][it["split"]] += 1
        d["licences"][f"{it['source']}: {it['licence']}"] += 1
        for k, v in it["suit"].items():
            d[k] += int(v)
    # suspected label noise among image-level photos
    noise = []
    try:
        from pollinex_ai.species import cnn_available, embed_cnn
        pool = [it for it in ok if it["label"] is None]
        if cnn_available() and pool:
            def centre(a):
                h, w = a.shape[:2]
                return a[int(h * .1):h - int(h * .1), int(w * .1):w - int(w * .1)]
            V = np.stack([embed_cnn(centre(np.array(Image.open(it["path"]).convert("RGB")))) for it in pool])
            S = V @ V.T
            np.fill_diagonal(S, -1)
            for i, it in enumerate(pool):
                nn = np.argsort(-S[i])[:5]
                sp = {pool[j]["species"] for j in nn}
                if len(sp) == 1 and it["species"] not in sp and S[i, nn[-1]] >= 0.80:
                    noise.append({"file": str(it["path"].relative_to(ROOT)), "label": it["species"], "neighbours_say": sp.pop(),
                                  "min_neighbour_cosine": round(float(S[i, nn[-1]]), 3)})
    except Exception as e:  # noqa: BLE001
        noise = [{"error": f"label-noise check skipped: {e}"}]
    rev_file = PROC / "label_review.csv"
    reviewed = {r["file"]: r for r in csv.DictReader(rev_file.open(encoding="utf-8"))} if rev_file.exists() else {}
    for n in noise:
        if "file" in n and n["file"] in reviewed:
            n["review"] = f"{reviewed[n['file']]['decision']}: {reviewed[n['file']]['note']}"
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "images_checked": len(items), "decoded_ok": len(ok),
              "corrupt": corrupt, "smaller_than_160px": tiny, "exact_duplicate_groups": len(exact),
              "near_duplicate_pairs": len(near), "cross_split_leakage_pairs": leaks,
              "per_species": {k: {**{kk: vv for kk, vv in v.items() if not isinstance(vv, Counter)},
                                  "sources": dict(v["sources"]), "splits": dict(v["splits"]), "licences": dict(v["licences"])}
                              for k, v in sorted(per.items())},
              "suspected_label_noise": noise,
              "suitability_rule": "closeup_structure_candidate = boxes exist AND largest box >= 15 % of the image AND >= 160 px "
                                  "min side; it says a flower is large enough to annotate structures, not that they are visible"}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "dataset_quality_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    L = ["# Dataset quality audit", "", f"_Generated {report['generated_at']} by `datasets/scripts/dataset_quality_audit.py`._", "",
         f"Images checked **{len(items)}** · decoded **{len(ok)}** · corrupt **{len(corrupt)}** · < 160 px **{len(tiny)}** · "
         f"exact-duplicate groups **{len(exact)}** · near-duplicate pairs **{len(near)}** · "
         f"**cross-split leakage pairs {len(leaks)}** · suspected label noise **{len([n for n in noise if 'file' in n])}** (review list)", "",
         "| Species | Images | Recognition | Detection (boxes) | Close-up structure candidates | Sources | Splits |", "|---|--:|--:|--:|--:|---|---|"]
    for k, v in report["per_species"].items():
        L.append(f"| {k} | {v['images']} | {v['recognition']} | {v['detection']} | {v['closeup_structure_candidate']} | "
                 f"{v['sources']} | {v['splits']} |")
    L += ["", "## Licences", "", "| Species | Licence counts |", "|---|---|"]
    L += [f"| {k} | {v['licences']} |" for k, v in report["per_species"].items()]
    if leaks:
        L += ["", "## Cross-split leakage pairs", ""] + [f"- `{x['a']}` ({x['a_split']}) ~ `{x['b']}` ({x['b_split']}), Hamming {x['hamming']}"
                                                         f"{' - resolved: test member excluded from evaluation (datasets/processed/leakage_exclusions.txt)' if x['resolved_by_test_exclusion'] else ' - UNRESOLVED'}"
                                                         for x in leaks]
    if any("file" in n for n in noise):
        L += ["", "## Suspected label noise (for human review; labels NOT changed)", ""]
        L += [f"- `{n['file']}`: labelled {n['label']}, 5 nearest neighbours are {n['neighbours_say']} (cos >= {n['min_neighbour_cosine']})"
              f" - {n.get('review', 'NOT YET REVIEWED')}" for n in noise if "file" in n]
    L += ["", report["suitability_rule"], ""]
    (REPORTS / "dataset_quality_audit.md").write_text("\n".join(L))
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
