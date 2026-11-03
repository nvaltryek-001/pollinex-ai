#!/usr/bin/env python3
"""Train + evaluate the CPU flower detector on the prepared USDA fruit-flower data.

Protocol (no test-set tuning):
  * fit pixel classifiers on TRAIN images only (masks -> pixel labels, sampled with hard negatives)
  * choose post-processing params (threshold / min_area / peak_distance) by mAP@0.5 on VAL only
  * evaluate ONCE on TEST and write reports

Variants compared on the same protocol (baseline + ablation):
  A  whiteness-Otsu      : no learning, Otsu threshold on the "whiteness" channel
  B  hgb-colour          : gradient-boosted trees on 12 per-pixel colour features
  C  hgb-full (deployed) : + multi-scale smoothed colour, gradient, LoG and local-contrast features

Usage:  python ai-engine/training/train_detector.py [--work-side 1280] [--quick]
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import HistGradientBoostingClassifier

ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
sys.path.insert(0, str(ENGINE))
from pollinex_ai.detector import instances_from_prob  # noqa: E402
from pollinex_ai.features import FEATURE_VERSION, pixel_features  # noqa: E402
from pollinex_ai.metrics import count_errors, detection_report  # noqa: E402

DATA = ROOT / "datasets" / "processed" / "usda_fruit_flower"
REPORTS = ENGINE / "reports"
MODELS = ENGINE / "models"
SEED = 20261102
N_BASE = 12


def load_split(records, split):
    return [r for r in records if r["split"] == split]


def load_pair(r, side):
    img = np.array(Image.open(DATA / "images" / f"{r['uid']}.jpg").convert("RGB"))
    mask = np.array(Image.open(DATA / "masks" / f"{r['uid']}.png")) > 0
    h, w = img.shape[:2]
    s = side / max(h, w)
    nw, nh = int(round(w * s)), int(round(h * s))
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA), \
        cv2.resize(mask.astype(np.uint8), (nw, nh), interpolation=cv2.INTER_NEAREST).astype(bool), s


def sample_pixels(feats, mask, rng, n_pos=3000, n_neg=6000):
    fg = np.flatnonzero(mask.ravel())
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~mask
    hard = np.flatnonzero(ring.ravel())
    bg = np.flatnonzero(~mask.ravel())
    pos = rng.choice(fg, min(n_pos, len(fg)), replace=False) if len(fg) else np.array([], int)
    nh = min(n_neg // 3, len(hard))
    neg = np.concatenate([rng.choice(hard, nh, replace=False) if nh else np.array([], int),
                          rng.choice(bg, min(n_neg - nh, len(bg)), replace=False)])
    f = feats.reshape(-1, feats.shape[-1])
    X = np.concatenate([f[pos], f[neg]])
    y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    return X, y


def otsu_whiteness_prob(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    white = (hsv[..., 2] / 255.0) * (1 - hsv[..., 1] / 255.0)
    u8 = (white * 255).astype(np.uint8)
    t, _ = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # soft score: distance above the Otsu threshold, mapped into [0, 1]; 0.5 == threshold
    return np.clip(0.5 + (white - t / 255.0) * 2.0, 0, 1).astype(np.float32)


def gt_boxes_scaled(r, s):
    return np.array([[v * s for v in b] for b in r["boxes"]], dtype=np.float32).reshape(-1, 4)


def predict_sets(prob_maps, params):
    preds = []
    for prob in prob_maps:
        inst = instances_from_prob(prob, params["threshold"], params["min_area"], params["peak_distance"])
        preds.append({"boxes": [i[0] for i in inst], "scores": [i[1] for i in inst]})
    return preds


def tune(prob_maps, gts, grid):
    best, best_p, rows = -1, None, []
    for th, ma, pdist in itertools.product(*grid):
        p = {"threshold": th, "min_area": ma, "peak_distance": pdist}
        rep = detection_report(predict_sets(prob_maps, p), gts)
        rows.append({**p, "val_mAP50": rep["mAP50"], "val_mAP50_95": rep["mAP50_95"]})
        if rep["mAP50"] > best:
            best, best_p = rep["mAP50"], p
    return best_p, rows


def seg_scores(prob_maps, masks, th):
    tp = fp = fn = 0
    for p, m in zip(prob_maps, masks):
        pr = p >= th
        tp += int((pr & m).sum()); fp += int((pr & ~m).sum()); fn += int((~pr & m).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"pixel_IoU": tp / max(tp + fp + fn, 1), "pixel_precision": prec, "pixel_recall": rec,
            "pixel_F1": 2 * prec * rec / max(prec + rec, 1e-9)}


def draw_overlay(rgb, gts, preds, path):
    im = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    for b in gts:
        cv2.rectangle(im, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (255, 255, 0), 1)
    for b, s in zip(preds["boxes"], preds["scores"]):
        cv2.rectangle(im, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (40, 40, 230) if s < 0.6 else (60, 200, 60), 2)
    cv2.imwrite(str(path), im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-side", type=int, default=1280)
    ap.add_argument("--quick", action="store_true", help="smaller grid / fewer iterations (smoke test)")
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    records = json.loads((DATA / "records.json").read_text())
    tr, va, te = (load_split(records, s) for s in ("train", "val", "test"))
    print(f"train {len(tr)}  val {len(va)}  test {len(te)}  work_side {args.work_side}")
    REPORTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "figures").mkdir(exist_ok=True)

    t0 = time.time()
    Xs, ys = [], []
    for r in tr:
        img, m, _ = load_pair(r, args.work_side)
        X, y = sample_pixels(pixel_features(img), m, rng)
        Xs.append(X); ys.append(y)
    X, y = np.concatenate(Xs), np.concatenate(ys)
    print(f"pixel samples {X.shape}, positives {int(y.sum())}  ({time.time()-t0:.1f}s)")

    iters = 60 if args.quick else 250
    models = {
        "B_hgb_colour": HistGradientBoostingClassifier(max_iter=iters, learning_rate=0.1, max_leaf_nodes=31,
                                                       l2_regularization=1.0, random_state=SEED),
        "C_hgb_full": HistGradientBoostingClassifier(max_iter=iters, learning_rate=0.1, max_leaf_nodes=63,
                                                     l2_regularization=1.0, random_state=SEED),
    }
    t1 = time.time(); models["B_hgb_colour"].fit(X[:, :N_BASE], y); tB = time.time() - t1
    t1 = time.time(); models["C_hgb_full"].fit(X, y); tC = time.time() - t1
    print(f"fit B {tB:.1f}s  C {tC:.1f}s")

    def prob_maps(split_recs, variant):
        maps, masks, gts, imgs, lat = [], [], [], [], []
        for r in split_recs:
            img, m, s = load_pair(r, args.work_side)
            t = time.perf_counter()
            if variant == "A_whiteness_otsu":
                p = otsu_whiteness_prob(img)
            else:
                f = pixel_features(img)
                f2 = f.reshape(-1, f.shape[-1])
                if variant == "B_hgb_colour":
                    f2 = f2[:, :N_BASE]
                p = models[variant].predict_proba(f2)[:, 1].reshape(img.shape[:2]).astype(np.float32)
            lat.append((time.perf_counter() - t) * 1000)
            maps.append(p); masks.append(m); gts.append(gt_boxes_scaled(r, s)); imgs.append(img)
        return maps, masks, gts, imgs, lat

    grid = ([0.35, 0.5, 0.65], [6, 15], [0, 6]) if args.quick else \
        ([0.3, 0.4, 0.5, 0.6, 0.7, 0.8], [4, 8, 15, 30], [0, 3, 6, 10])
    results, chosen, tuning_rows = {}, {}, {}
    for variant in ("A_whiteness_otsu", "B_hgb_colour", "C_hgb_full"):
        vmaps, vmasks, vgts, _, _ = prob_maps(va, variant)
        g = grid if variant != "A_whiteness_otsu" else ([0.5, 0.55, 0.6], grid[1], grid[2])
        best_p, rows = tune(vmaps, vgts, g)
        chosen[variant], tuning_rows[variant] = best_p, rows
        val_rep = detection_report(predict_sets(vmaps, best_p), vgts)
        tmaps, tmasks, tgts, timgs, tlat = prob_maps(te, variant)  # TEST: evaluated once with frozen params
        tpreds = predict_sets(tmaps, best_p)
        test_rep = detection_report(tpreds, tgts)
        per_species = {}
        for sp in sorted({r["species"] for r in te}):
            idx = [i for i, r in enumerate(te) if r["species"] == sp]
            per_species[sp] = detection_report([tpreds[i] for i in idx], [tgts[i] for i in idx])
            per_species[sp].pop("ap_per_iou", None)
        results[variant] = {
            "params": best_p, "val": {k: val_rep[k] for k in ("mAP50", "mAP50_95")}, "test": test_rep,
            "test_per_species": per_species,
            "test_counting": count_errors([len(p["boxes"]) for p in tpreds], [len(g) for g in tgts]),
            "test_segmentation": seg_scores(tmaps, tmasks, best_p["threshold"]),
            "latency_ms_per_image_mean": float(np.mean(tlat)), "latency_ms_per_image_p95": float(np.percentile(tlat, 95)),
        }
        print(f"{variant}: val mAP50 {val_rep['mAP50']:.3f} | TEST mAP50 {test_rep['mAP50']:.3f} "
              f"mAP50-95 {test_rep['mAP50_95']:.3f} P {test_rep['precision@0.5']:.3f} R {test_rep['recall@0.5']:.3f}")
        if variant == "C_hgb_full":
            # error analysis: worst images + box-size breakdown of misses
            per_img = []
            for i, r in enumerate(te):
                rep = detection_report([tpreds[i]], [tgts[i]])
                per_img.append({"uid": r["uid"], "species": r["species"], "gt": len(tgts[i]),
                                "pred": len(tpreds[i]["boxes"]), "AP50": rep["mAP50"]})
            per_img.sort(key=lambda d: d["AP50"])
            from pollinex_ai.metrics import iou_matrix
            size_bins = {"small(<16px)": [0, 0], "medium(16-40px)": [0, 0], "large(>40px)": [0, 0]}
            for i in range(len(te)):
                g = tgts[i]
                if not len(g):
                    continue
                pb = np.array(tpreds[i]["boxes"]).reshape(-1, 4)
                hit = (iou_matrix(g, pb).max(1) >= 0.5) if len(pb) else np.zeros(len(g), bool)
                side = np.sqrt((g[:, 2] - g[:, 0]) * (g[:, 3] - g[:, 1]))
                for sd, h in zip(side, hit):
                    k = "small(<16px)" if sd < 16 else ("medium(16-40px)" if sd <= 40 else "large(>40px)")
                    size_bins[k][0] += 1; size_bins[k][1] += int(h)
            results[variant]["error_analysis"] = {
                "worst_images": per_img[:5], "best_images": per_img[-3:],
                "recall_by_gt_size_at_work_res": {k: {"n_gt": v[0], "recall@0.5": v[1] / max(v[0], 1)} for k, v in size_bins.items()},
            }
            for i in [0, len(te) // 2, len(te) - 1]:
                draw_overlay(timgs[i], tgts[i], tpreds[i], REPORTS / "figures" / f"test_overlay_{te[i]['uid']}.jpg")

    deployed = "C_hgb_full"
    bundle = {
        "model": models[deployed], "feature_version": FEATURE_VERSION,
        "params": {**chosen[deployed], "work_side": args.work_side, "low_conf": 0.6},
        "version": f"pixel-hgb-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "trained_on": "usda_fruit_flower train split (Dias, Tabb & Medeiros 2018, CC BY 4.0)",
        "species_in_training": sorted({r["species"] for r in tr}),
        "test_metrics": {k: results[deployed]["test"][k] for k in ("mAP50", "mAP50_95", "precision@0.5", "recall@0.5", "f1@0.5")},
    }
    joblib.dump(bundle, MODELS / "flower_pixel_hgb.joblib", compress=3)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "seed": SEED, "work_side": args.work_side,
        "quick": args.quick, "machine": {"platform": platform.platform(), "python": platform.python_version(),
                                          "cpu_count": __import__("os").cpu_count()},
        "data": {"train_images": len(tr), "val_images": len(va), "test_images": len(te),
                 "train_pixel_samples": int(len(y))},
        "fit_seconds": {"B_hgb_colour": tB, "C_hgb_full": tC},
        "protocol": "params tuned on val by mAP@0.5; test evaluated once; COCO-style 101-pt AP; IoU 0.50:0.95",
        "deployed_variant": deployed, "variants": results, "tuning_grid_rows": tuning_rows,
    }
    (REPORTS / "detector_evaluation.json").write_text(json.dumps(report, indent=2))
    print("saved", MODELS / "flower_pixel_hgb.joblib", (MODELS / "flower_pixel_hgb.joblib").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
