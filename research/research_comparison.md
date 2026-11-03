# Research Comparison Matrix

| Work | Type | Task | Data | Model | Real-world eval | Hardware needed | Species | What POLLINEX takes |
|---|---|---|---|---|---|---|---|---|
| FloPE (Shrestha et al., 2025) | PR | 6-DoF flower pose | Synthetic (3D Gaussian Splatting) | Teacher→student distillation | Yes, robot arms | RGB(-D) camera + robot | Not stated in abstract | Centre + facing-direction concept; image-space alignment vector |
| Broussard et al., 2023 | PR review | Artificial pollination methods | Literature | — | Summarised | Varies | Kiwifruit, tomato, apple, pear, almond, maize, date palm… | Species-specific strategy categories; env. factors |
| Zhang et al., 2025 | PR review | Autonomous pollination | Literature / bibliometrics | — | Summarised | Ground robots, UAVs | Multiple | detect → localise → plan pipeline |
| Singh et al., 2025/26 | PR review | Robot pollinators (greenhouse) | Literature | — | Summarised | Robots | Tomato (~60 %), kiwi (~25 %), strawberry… | Mechanism taxonomy; vibration parameter |
| Schouten et al., 2024 (EWD) | PR + DS | Multi-species flower detection | 2,002 imgs, 65,571 boxes, CC BY-NC | Faster R-CNN R50 | Hold-out test, mAP@0.5 0.82 (49 spp.) | Camera | 160 wildflowers | Tiling, annotation rules, open-set caution |
| Balfour et al., 2022 (DoPI) | PR data paper | Plant–pollinator interactions | ~100k records, GB only | — | — | — | 1,241 plants | Pollinator-group field (with geographic caveat) |
| Dias et al., 2018 | PR + DS | Fruit flower segmentation | Apple/peach/pear, CC BY 4.0 | Refined residual CNN | Cross-species tests | Camera | Apple, peach, pear | **Training data for our detector** |
| **POLLINEX AI (ours)** | OURS | Detection, species gallery, stage/structure/health heuristics, readiness rules, simulation | USDA fruit-flower set (+ user galleries) | SLIC + gradient-boosted region classifier (CPU baseline); YOLO11 recipe | Our held-out test split only; **no biological field validation** | Laptop + phone browser | 9 crop profiles (detector trained on 3) | — |

## Key differences

1. **Software-only, browser-delivered.** The reviewed systems assume robots or drones; POLLINEX targets a phone/laptop and stops at *decision support* and *simulation*.
2. **Explicit evidence labelling.** Every POLLINEX output carries its evidence class: trained-model output, heuristic, rule-based, or simulation.
3. **Open-set species handling.** Unlike closed-set classifiers, our gallery classifier returns `unknown` when similarity is below a calibrated threshold.
4. **Coverage honesty.** We have annotated detection data for 3 of the 9 target crops. For the other 6 the platform runs the generic flower detector and species knowledge base but reports `species: unknown` until reference images are added.
