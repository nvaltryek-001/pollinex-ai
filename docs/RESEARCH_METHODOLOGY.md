# Research Methodology

The full methodology (questions, data, training configurations, validation strategy, baselines, ablations, reproducibility and
the plan for biological validation) is in [`research/methodology.md`](../research/methodology.md). Summary:

| Element | Implementation |
|---|---|
| Independent splits | group-aware contiguous blocks; dHash leakage audit |
| No test tuning | all thresholds/configs chosen on validation; test evaluated once per variant |
| Baselines | Otsu whiteness (no learning) and colour-only learner on the same protocol |
| Ablation | feature set (12 vs 36 channels); inference resolution × stride |
| Error analysis | recall by size; worst images; overlay figures; per-species AP; AP vs IoU |
| Open-set evaluation | background-crop rejection; leave-one-species-out |
| Reproducibility | fixed seeds; scripts regenerate data, models and reports; machine info recorded |
| Biological claims | none; randomised block design (natural vs manual vs app-assisted) specified for future trials |

Training configurations: see `ai-engine/training/train_detector.py` (constants and argparse defaults) and the `params` block
saved inside each model bundle and report.
