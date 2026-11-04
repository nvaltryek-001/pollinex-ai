#!/usr/bin/env python3
"""Pre-registered selection between the DEPLOYED YOLO11 model and a newly trained CANDIDATE (written 2026-11-04,
before the candidate was trained).

Rule: the candidate replaces the deployed model iff its mean per-species mAP@0.5 on the VALIDATION split
(apple, peach, pear, sunflower; detector_analysis.py) is higher than the deployed model's. The test split is not used
for the decision; it is reported afterwards for whichever model is deployed. Writes ai-engine/reports/yolo11_selection.json
and, if the candidate wins, copies it (+ sidecar with its validation-chosen operating threshold) into ai-engine/models/.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
R = ENGINE / "reports"
SPECIES = ("apple", "peach", "pear", "sunflower")


def val_score(tag: str):
    rep = json.loads((R / f"detector_analysis_{tag}_val.json").read_text())
    per = {sp: rep["per_species"][sp]["mAP50"] for sp in SPECIES if sp in rep["per_species"]}
    return sum(per.values()) / len(per), per, rep["operating_threshold"]


dep, dep_per, _ = val_score("yolo11")
cand, cand_per, cand_thr = val_score("candidate")
replace = cand > dep
decision = {"generated_at": datetime.now(timezone.utc).isoformat(),
            "rule": "replace iff candidate mean per-species VAL mAP@0.5 > deployed", "deployed_val": {"mean": dep, **dep_per},
            "candidate_val": {"mean": cand, **cand_per}, "candidate_replaces_deployed": replace}
if replace:
    src = ENGINE / "runs" / "export"
    cfg = json.loads((src / "flower_yolo11n.json").read_text())
    cfg.update({"conf_threshold": cand_thr, "conf_threshold_source": "argmax F1 on the validation split"})
    shutil.copy2(src / "flower_yolo11n.onnx", ENGINE / "models" / "flower_yolo11n.onnx")
    (ENGINE / "models" / "flower_yolo11n.json").write_text(json.dumps(cfg, indent=2))
(R / "yolo11_selection.json").write_text(json.dumps(decision, indent=2))
print(json.dumps(decision, indent=2))
