#!/usr/bin/env python3
"""Reproducible evaluation of the DEPLOYED POLLINEX AI models on the repository datasets.

    python scripts/evaluate_deployed_models.py            # integrity audit + detection + species classification
    python scripts/evaluate_deployed_models.py --skip-classification

What it does (no training, no tuning - the shipped artifacts in ai-engine/models are only loaded and run):
  1. Dataset integrity audit: every image decodes, every YOLO label row is valid, species labels are known,
     no exact-duplicate image (SHA-256 of decoded pixels) appears in more than one split, test leakage exclusions applied.
  2. Flower DETECTION (YOLO11n ONNX, the same loader the API uses) on the held-out test splits that have boxes:
     USDA apple/peach/pear orchard images and TF Flower Detection sunflower images.
     Reports precision/recall @ IoU 0.5, mAP@0.5 and mAP@0.5:0.95, overall and per species.
  3. Species CLASSIFICATION (deployed reference gallery, loaded from disk) on the held-out test crops/photos, built with
     exactly the same functions and seed as the gallery build. Reports accuracy, macro-F1, confusion matrix and
     per-species precision/recall/F1, overall and per source.

Detection and classification are separate tasks and are reported in separate sections; they are never combined.
Writes ai-engine/reports/deployed_model_evaluation.json and docs/MODEL_EVALUATION_RESULTS.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ai-engine"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "training"))
from pollinex_ai.detector import OnnxYoloDetector, load_default_detector  # noqa: E402
from pollinex_ai.metrics import classification_report, detection_report  # noqa: E402
from evaluate_detector_on import excluded_stems, image_list, label_path  # noqa: E402

PROC = ROOT / "datasets" / "processed"
SPECIES = ["apple", "peach", "pear", "sunflower", "hibiscus", "tomato", "strawberry", "brinjal", "chilli"]
DET_SETS = {"usda_fruit_flower": PROC / "usda_fruit_flower", "tf_flower_detection_sunflower": PROC / "tf_flower_detection_sunflower"}
IMAGE_SETS = {"inat_flowering": PROC / "inat_flowering", "commons_flowers": PROC / "commons_flowers"}


def pixel_hash(p: Path) -> str:
    with Image.open(p) as im:
        return hashlib.sha256(im.convert("RGB").tobytes()).hexdigest()


def audit() -> dict:
    out, problems = {}, []
    excl = excluded_stems()
    for name, root in DET_SETS.items():
        seen: dict[str, str] = {}
        cross, n_img, n_box, bad_rows = [], 0, 0, 0
        for split in ("train", "val", "test"):
            ims = image_list(root, split)
            for p in ims:
                n_img += 1
                try:
                    h = pixel_hash(p)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"{name}/{split}/{p.name}: does not decode ({e})")
                    continue
                if h in seen and seen[h] != split:
                    cross.append(f"{p.name} ({split}) == image in {seen[h]}")
                seen.setdefault(h, split)
                lp = label_path(p)
                if not lp.exists():
                    problems.append(f"{name}/{split}/{p.name}: missing label file")
                    continue
                for row in lp.read_text().split("\n"):
                    if not row.strip():
                        continue
                    v = row.split()
                    ok = len(v) == 5 and all(0.0 <= float(x) <= 1.0 for x in v[1:]) and float(v[3]) > 0 and float(v[4]) > 0
                    bad_rows += not ok
                    n_box += ok
        out[name] = {"images": n_img, "boxes": n_box, "invalid_label_rows": bad_rows, "cross_split_exact_duplicates": cross}
    for name, root in IMAGE_SETS.items():
        seen, cross, counts, unknown_labels = {}, [], Counter(), set()
        for split in ("train", "val", "test"):
            for sp_dir in sorted(d for d in (root / split).iterdir() if d.is_dir()) if (root / split).is_dir() else []:
                if sp_dir.name not in SPECIES:
                    unknown_labels.add(sp_dir.name)
                for p in sorted(sp_dir.glob("*.jpg")):
                    if split == "test" and p.stem in excl:
                        continue
                    try:
                        h = pixel_hash(p)
                    except Exception as e:  # noqa: BLE001
                        problems.append(f"{name}/{split}/{sp_dir.name}/{p.name}: does not decode ({e})")
                        continue
                    if h in seen and seen[h] != split:
                        cross.append(f"{sp_dir.name}/{p.name} ({split}) == image in {seen[h]}")
                    seen.setdefault(h, split)
                    counts[f"{split}/{sp_dir.name}"] += 1
        out[name] = {"images": sum(counts.values()), "per_split_species": dict(sorted(counts.items())),
                     "unknown_species_folders": sorted(unknown_labels), "cross_split_exact_duplicates": cross}
    out["leakage_exclusions_applied_to_test"] = sorted(excl)
    out["problems"] = problems
    out["passed"] = not problems and all(not v.get("cross_split_exact_duplicates") and not v.get("invalid_label_rows")
                                         and not v.get("unknown_species_folders") for k, v in out.items() if isinstance(v, dict))
    return out


def detection(det) -> dict:
    res = {}
    for name, root in DET_SETS.items():
        ims = image_list(root, "test")
        preds, gts, sp_of, lat = [], [], [], []
        for p in ims:
            rgb = np.array(Image.open(p).convert("RGB"))
            H, W = rgb.shape[:2]
            rows = [list(map(float, ln.split()[1:])) for ln in label_path(p).read_text().splitlines() if ln.strip()]
            gts.append(np.array([[(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H] for x, y, w, h in rows],
                                np.float32).reshape(-1, 4))
            t = time.perf_counter()
            r = det.detect(rgb, conf_threshold=0.05) if isinstance(det, OnnxYoloDetector) else det.detect(rgb)
            lat.append((time.perf_counter() - t) * 1000)
            preds.append({"boxes": [d.box for d in r.detections], "scores": [d.score for d in r.detections]})
            sp_of.append("sunflower" if "sunflower" in name else p.stem.split("_")[0])
        overall = detection_report(preds, gts)
        thr = float(getattr(det, "conf_threshold", 0.30) or 0.30)
        at = detection_report([{"boxes": [b for b, sc in zip(q["boxes"], q["scores"]) if sc >= thr],
                                "scores": [sc for sc in q["scores"] if sc >= thr]} for q in preds], gts)
        per = {}
        for sp in sorted(set(sp_of)):
            idx = [i for i, s in enumerate(sp_of) if s == sp]
            r = detection_report([preds[i] for i in idx], [gts[i] for i in idx])
            per[sp] = {"images": len(idx), "boxes": int(sum(len(gts[i]) for i in idx)), **{k: r[k] for k in KEYS}}
        res[name] = {"images": len(ims), "boxes": int(sum(len(g) for g in gts)), **{k: overall[k] for k in KEYS},
                     "deployed_threshold": thr, "precision_at_deployed_threshold": at["precision@0.5"],
                     "recall_at_deployed_threshold": at["recall@0.5"], "per_species": per, "latency_ms_mean": float(np.mean(lat))}
    return res


KEYS = ("precision@0.5", "recall@0.5", "mAP50", "mAP50_95")


def classification() -> dict:
    from build_species_gallery_multi import load_all, predict  # heavy import: embeds every split with the shipped ONNX
    from pollinex_ai.pipeline import GALLERY_PATH
    from pollinex_ai.species import BACKGROUND, UNKNOWN, SpeciesGallery

    g = SpeciesGallery.load(GALLERY_PATH)
    enabled = sorted(set(g.labels) - {BACKGROUND})
    data = load_all(g.meta["embed_version"])  # same functions + seed as the build -> identical test items
    labels = enabled + [UNKNOWN]
    by_source, all_t, all_p = {}, [], []
    for name, items in data["test"].items():
        if not items:
            continue
        yt = [y if y in enabled else UNKNOWN for y, _ in items]
        yp = predict(g, items)
        all_t += yt
        all_p += yp
        rep = classification_report(yt, yp, labels)
        by_source[name] = {"n": len(items), "accuracy": rep["accuracy"], "macro_f1": rep["macro_f1"]}
        unsupported = sorted({y for y, _ in items} - set(enabled))
        if unsupported:
            by_source[name]["unsupported_true_species_predicted_as"] = {
                s: dict(Counter(p for (y, _), p in zip(items, yp) if y == s)) for s in unsupported}
    overall = classification_report(all_t, all_p, labels)
    true_counts = Counter(all_t)
    return {"gallery": {"embedding": g.meta["embed_version"], "k": g.k, "threshold": g.threshold,
                        "enabled_species": enabled, "references": dict(Counter(g.labels))},
            "labels": labels, "test_items": len(all_t), "true_label_counts": dict(true_counts),
            "accuracy": overall["accuracy"], "macro_f1": overall["macro_f1"],
            "per_species": overall["per_class"], "confusion_matrix": overall["confusion_matrix"], "by_source": by_source,
            "note": "Species not enabled in the gallery (strawberry) are scored as correct only when predicted 'unknown'. "
                    "'usda_test_background' items are non-flower crops whose correct answer is 'unknown'."}


def markdown(rep: dict) -> str:
    L = ["# Deployed model evaluation results", "",
         f"Generated {rep['generated_at']} by `python scripts/evaluate_deployed_models.py` on the repository datasets. "
         "Nothing was trained or tuned by this script; the shipped artifacts were loaded and run on held-out **test** splits.", "",
         "Detection and species classification are different tasks and are reported separately. Neither number says anything "
         "about fruit, disease, pollen viability or fertilisation, which no model in this project predicts.", ""]
    a = rep["integrity"]
    L += ["## 1. Dataset integrity", "", f"Overall: **{'passed' if a['passed'] else 'issues found'}**.", "",
          "| Dataset | Images | Boxes | Invalid label rows | Cross-split exact duplicates |", "|---|--:|--:|--:|--:|"]
    for k, v in a.items():
        if isinstance(v, dict):
            L.append(f"| {k} | {v['images']} | {v.get('boxes', '-')} | {v.get('invalid_label_rows', '-')} | {len(v['cross_split_exact_duplicates'])} |")
    L += ["", f"Test images excluded for near-duplicate leakage: {', '.join(a['leakage_exclusions_applied_to_test']) or 'none'}."]
    if a["problems"]:
        L += ["", "Problems:"] + [f"- {p}" for p in a["problems"][:50]]
    if "detection" in rep:
        d = rep["detection"]
        L += ["", f"## 2. Flower detection - {rep['detector']}", "",
              "IoU 0.5 for precision/recall/mAP@0.5; mAP@0.5:0.95 averages IoU 0.50-0.95. Confidence floor 0.05 for the PR curve.", "",
              "| Test set | Species | Images | Boxes | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |", "|---|---|--:|--:|--:|--:|--:|--:|"]
        for name, v in d.items():
            L.append(f"| {name} | **all** | {v['images']} | {v['boxes']} | {v['precision@0.5']:.3f} | {v['recall@0.5']:.3f} | {v['mAP50']:.3f} | {v['mAP50_95']:.3f} |")
            for sp, s in v["per_species"].items():
                if len(v["per_species"]) > 1:
                    L.append(f"| | {sp} | {s['images']} | {s['boxes']} | {s['precision@0.5']:.3f} | {s['recall@0.5']:.3f} | {s['mAP50']:.3f} | {s['mAP50_95']:.3f} |")
        L += ["", "Precision/recall above are at the 0.05 confidence floor (all candidate boxes). At the deployed threshold:", ""]
        L += [f"- {n}: threshold {v['deployed_threshold']:.2f} -> precision {v['precision_at_deployed_threshold']:.3f}, "
              f"recall {v['recall_at_deployed_threshold']:.3f}" for n, v in d.items()]
        L += ["", "No box annotations exist for hibiscus, tomato, strawberry, brinjal or chilli, so **no detection performance is "
              "claimed for those species**."]
    if "classification" in rep:
        c = rep["classification"]
        L += ["", "## 3. Species classification - reference gallery", "",
              f"Gallery `{c['gallery']['embedding']}`, k={c['gallery']['k']}, threshold {c['gallery']['threshold']}. "
              f"{c['test_items']} held-out test items.", "",
              f"**Accuracy {c['accuracy']:.3f} · macro-F1 {c['macro_f1']:.3f}**", "",
              "| Species | Precision | Recall | F1 | Test support |", "|---|--:|--:|--:|--:|"]
        for sp, v in c["per_species"].items():
            L.append(f"| {sp} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1']:.3f} | {v['support']} |")
        L += ["", "Confusion matrix (rows = true, columns = predicted):", "", "| true \\ pred | " + " | ".join(c["labels"]) + " |",
              "|---|" + "--:|" * len(c["labels"])]
        for lab, row in zip(c["labels"], c["confusion_matrix"]):
            L.append(f"| {lab} | " + " | ".join(str(x) for x in row) + " |")
        L += ["", "By test source:", "", "| Source | Items | Accuracy | Macro-F1 |", "|---|--:|--:|--:|"]
        for k, v in c["by_source"].items():
            L.append(f"| {k} | {v['n']} | {v['accuracy']:.3f} | {v['macro_f1']:.3f} |")
        L += ["", c["note"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-detection", action="store_true")
    ap.add_argument("--skip-classification", action="store_true")
    args = ap.parse_args()
    rep: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    print("integrity audit ...", flush=True)
    rep["integrity"] = audit()
    print("  passed:", rep["integrity"]["passed"], flush=True)
    if not args.skip_detection:
        det = load_default_detector()
        rep["detector"] = f"{det.backend} {det.version}"
        print("detection on", rep["detector"], "...", flush=True)
        rep["detection"] = detection(det)
        for k, v in rep["detection"].items():
            print(f"  {k}: mAP50 {v['mAP50']:.3f} mAP50-95 {v['mAP50_95']:.3f} P {v['precision@0.5']:.3f} R {v['recall@0.5']:.3f}")
    if not args.skip_classification:
        print("species classification ...", flush=True)
        rep["classification"] = classification()
        c = rep["classification"]
        print(f"  accuracy {c['accuracy']:.3f} macro-F1 {c['macro_f1']:.3f} over {c['test_items']} items")
    (ENGINE / "reports" / "deployed_model_evaluation.json").write_text(json.dumps(rep, indent=2))
    (ROOT / "docs" / "MODEL_EVALUATION_RESULTS.md").write_text(markdown(rep))
    print("wrote ai-engine/reports/deployed_model_evaluation.json and docs/MODEL_EVALUATION_RESULTS.md")
    if not rep["integrity"]["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
