# POLLINEX AI: Final Release Report

_Report date: 2026-11-04 (updated after the second YOLO11 run, gallery v2, the Commons dataset and deployment).
Repository: https://github.com/nvaltryek-001/pollinex-ai (branch `main`). **Live demo: https://pollinex-api.onrender.com**._

## Final status (2026-11-04, completion pass)

This section supersedes the updates below it. Every claim links to a file or to a CI run.

### What was added in this pass
* **Species knowledge base:** `ai-engine/pollinex_ai/knowledge/species_botany.json` covers all 9 species. Each record has
  family, flower, petals, visible reproductive structures, flowering, flowering period (with regional notes), pollination
  mechanism, pollinators, self/cross-pollination, fruit (name, type, characteristics), agricultural relevance and sources.
  * The loader validates every field and source.
  * The app shows it as *reference knowledge, not from this image*.
  * See [`SPECIES_KNOWLEDGE_BASE.md`](SPECIES_KNOWLEDGE_BASE.md).
* **Fruit:** no fruit dataset or model exists. This is stated in the UI under every species panel, in the per-scan PDF, on the
  Help page and in the docs. A separate future fruit workflow is documented. Fruit and flower recognition stay separate concepts.
* **Results page:**
  * a species information panel that follows the predicted, or user-corrected, species;
  * a *How this result was produced* card with scan date, source, mode, detector and gallery versions, the method of every
    module, limitations and recommended next steps;
  * on the scan detail page, a **PDF report** (`GET /api/v1/reports/scans/{id}.pdf`), a CSV of all scans and JSON.
* **Help & documentation page** (`/app/help`), which brings the app to 21 pages.
* **Reproducible evaluation:** `scripts/evaluate_deployed_models.py` runs the shipped models on the repository test splits.
  * It reproduced the committed numbers exactly; results are in [`MODEL_EVALUATION_RESULTS.md`](MODEL_EVALUATION_RESULTS.md).
  * Detection results (computed on box-annotated data only):

    | Test set | mAP@0.5 | mAP@0.5:0.95 | Precision @ 0.30 | Recall @ 0.30 | Per species mAP@0.5 |
    |---|--:|--:|--:|--:|---|
    | USDA | 0.593 | 0.332 | 0.647 | 0.578 | apple 0.602, peach 0.568, pear 0.609 |
    | Sunflower | 0.871 | 0.694 | 0.817 | 0.837 | — |

  * Species classification, reported separately: 1,182 test items, accuracy 0.874, macro-F1 0.862, with a confusion matrix and per-species P/R/F1.
  * **No detection performance is claimed for hibiscus, tomato, strawberry, brinjal or chilli**, because no boxes exist for them.
* **Dataset integrity audit:** a CI test (`test_dataset_integrity_audit_passes`) checks that all images decode, that label rows are valid, that species folders are known, that no exact duplicate crosses splits, and that the leakage exclusion is applied. It passed.
* **Audit checklist** for all 21 modules plus data and deployment: [`PROJECT_AUDIT_CHECKLIST.md`](PROJECT_AUDIT_CHECKLIST.md).
* `/api/v1/health` now reports `database_backend` (the dialect name only, never the URL).

### Tests
**CI run [41821905369](https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41821905369)** on `5335a16`: all 5 jobs passed.

| Suite | Result |
|---|---|
| AI engine + simulator | 47 passed |
| Backend (SQLite + PostgreSQL 16 migrations, startup) | 27 passed |
| Vitest | 11 passed |
| TypeScript check + production build | passed |
| Playwright E2E (desktop + mobile, fake camera) | 16 passed |
| Docker images | built |
| Windows fresh clone | engine 47, backend 27, Vitest 11, Playwright 14 passed |
| Evaluate deployed models (`[evaluate]`, run 41820896337) | passed |

**Skipped on purpose:** 2 screenshot-capture tests on Windows. They are documentation screenshots, not checks.

**Failure found and fixed:** in the previous run (41820896150), the new mobile E2E step timed out. Playwright reported that its click on the history link was intercepted by the *No pollination actions logged* placeholder, apparently while the page layout was still shifting. The test now opens the scan through the link's `href`. The same flow passed on desktop, including the PDF and CSV downloads.

### Deployment (verified facts only)
* **Render service `pollinex-api`:** commit `5335a16` is live (deploy `dep-dblhilbm8hqs739akgig`, started manually).
  Later commits only change docs and workflows. The live smoke run [41822914659](https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41822914659) passed:
  * health ok, with YOLO11 ONNX and 8 gallery species;
  * the SPA deep links `/app/scanner` and `/app/help` are served;
  * a JS asset returns 200, and OpenAPI lists 50 paths, including the per-scan PDF;
  * unauthenticated `/scans` and `/reports/scans/1.pdf` return 401;
  * `database_backend = sqlite`, which confirms that the data is **not yet persistent**.
* **Persistent PostgreSQL: not yet connected (owner action).**
  * `pollinex-db` exists, but its connection string cannot be read with the available tools, and it must not be committed.
  * Steps: Render → `pollinex-db` → copy the **Internal Database URL** → `pollinex-api` → *Environment* → `DATABASE_URL` → save, then redeploy.
  * Then check that `/api/v1/health` shows `"database_backend": "postgresql"`, and that an account and a scan survive *Restart service*.
* **Auto-deploy: not working (owner action).**
  * The service has `autoDeploy: yes`, but neither `ec1b842` nor `4e29813` triggered a deploy. Deploys were started manually through the API.
  * Fix: give Render's GitHub app access to the repository, or add a deploy-hook secret. Steps are in [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md).
* **Vercel: blocked.** The connected account returns HTTP 403 on project creation, and the team has 0 projects. It is optional, because Render serves the UI; import steps are in the deployment guide.
* **Secrets:** `JWT_SECRET` is set only on Render. No credentials are in the repository.

### Later the same evening (15-minute audit pass)
* **Mobile layout bug fixed.** Pages could scroll sideways on phones, by 53–56 px on Model evaluation, because grid children
  kept their minimum content width and several tables had no scroll box. Grid children may now shrink, and cards scroll their
  own wide content. A new E2E test checks 15 pages for sideways scrolling at 390 px. It caught the bug; the fix passed CI
  run 41835299076. The mobile history-link click from the earlier failure now works without a workaround.
* **Vitest:** 2 new species-panel tests, so Vitest is now 13. Total automated tests: 103.
* **Per-species dataset inventory:** `datasets/reports/species_inventory.json` is built from the files on disk; the audit
  was re-run with unchanged counts. It includes the status of the 10 external datasets.
* **End-to-end inference on real photos of all 9 species** (`scripts/sample_inference_check.py`): the top flower's species
  matched the photo label in 29/40 (close-up) and 24/40 (auto) photos of the 8 supported species, and strawberry got 0/5.
  Auto mode is weaker on whole-scene photos because it classifies the detection crop. This is documented as a limitation and
  has not been fixed yet.
* **Windows guide** for `N:\pollinex-ai`: [`LOCAL_SETUP.md`](LOCAL_SETUP.md).

### Still not done
* There are no reproductive-structure, stage, health or fruit models, because no annotations exist for them.
* There are no boxes for 5 species.
* Strawberry is not AI-supported.
* Brinjal and chilli rest on limited evidence.
* The phone camera has not been tested on a real device over HTTPS.
* Species recognition in auto mode on whole-scene photos is weaker than in close-up mode (see above).

---

> **Update (later the same day).** Sections 1–8 below were written for the first release. These numbers replace the older figures:
> * **Images:** **1,985**. The 506 new ones come from Wikimedia Commons, and the quality audit (`datasets/reports/dataset_quality_audit.md`) found 0 corrupt files, 0 exact duplicates and 1 leakage pair, which is excluded from evaluation.
> * **Per species:**
>
>   | Species | Images |
>   |---|--:|
>   | apple | 155 |
>   | peach | 95 |
>   | pear | 47 |
>   | sunflower | 828 |
>   | hibiscus | 256 |
>   | tomato | 347 |
>   | strawberry | 44 |
>   | brinjal | 131 |
>   | chilli | 82 |
> * **Species gallery v2:**
>   * ImageNet MobileNetV3 embeddings plus 540 real background references, chosen on validation.
>   * **8 species are AI-supported.** Brinjal and chilli have *limited evidence* (11 and 7 test images); strawberry is not supported.
>   * Test: accuracy **0.874**, macro-F1 **0.862**. Background rejection rose from 0.095 to **0.705**.
>   * An explicit `uncertain` flag and a support status are attached to every species result.
> * **Detector:** **YOLO11n at 960 px** replaced the 800 px model under the validation-only selection rule.
>   * Test mAP@0.5: **USDA 0.593** (800 px model: 0.541; pixel model: 0.410) and **sunflower 0.871** (94 images).
>   * Per species: apple 0.602, peach 0.568, pear 0.609, sunflower 0.871.
>   * Operating threshold 0.30, chosen on validation.
>   * ONNX matches PyTorch on 85.5 % of boxes at IoU ≥ 0.8.
>   * Admins can switch between YOLO11, the pixel model and auto; the switch falls back safely.
> * **Reproductive structures:**
>   * Full CVAT workflow, an annotation-batch builder (283 real images selected), and a COCO→YOLO converter.
>   * A structure-model hook that switches classes to `trained_model` once a model trained on real annotations is installed.
>   * Still **0 structure annotations**, so these outputs remain heuristics.
> * **Research:** 50 papers checked against OpenAlex (`research/papers/`) and numbered citation documents in the Drive folder.
> * **Deployment:**
>   * Render free web service: the Docker image builds the React app, and FastAPI serves it on the same origin.
>   * Data is not persistent until the created Render PostgreSQL URL is set as `DATABASE_URL`.
>   * Vercel project creation was refused (HTTP 403) by the connected account.
> * **Tests:** CI run 41816002898 on `af34e3c` passed all 5 jobs, including the Docker image build with the frontend stage:
>
>   | Suite | Result |
>   |---|---|
>   | AI engine + simulator | 45 passed |
>   | Backend | 27 passed |
>   | Vitest | 11 passed |
>   | Playwright | 14 passed |
>   | Windows | same suites; Playwright 12 passed, 2 screenshot tests skipped |
>
>   The live smoke test passed against the public demo: health ok with YOLO11 and 8 species, the app served on a deep link, an asset returned 200, and an unauthenticated `/api/v1/scans` returned 401.
> * **Fixes found while testing:**
>   * The Datasets page crashed on per-species count objects. A page error boundary now catches render errors.
>   * Close-up analysis ran GrabCut four times per flower (now about 3 s → 0.5 s per image).
>   * E2E waits now suit shared CI runners.
>   * Hosted `postgres://` URLs are now mapped to psycopg 3.


Every number here comes from a committed report file or a test run named below. Nothing is estimated. "Not done" items are
listed in §8.

## 1. Summary
| Question | Answer (verified) |
|---|---|
| Real images in the repository | **1,479**: 718 with flower boxes (USDA 90, TF sunflower 628) + 761 iNaturalist photos with species labels only. 0 corrupt, 0 exact duplicates (`datasets/reports/dataset_inventory.md`). |
| Species with images | **9 of 9**, but strawberry (15), brinjal (20) and chilli (28) are too few to support. |
| Species the AI recognises (gallery) | **6 of 9**: apple, peach, pear, sunflower, hibiscus, tomato. Chosen by a validation gate fixed before any results existed. |
| Species the detector was trained on | **4 of 9**: apple, peach, pear, sunflower. No boxes exist for the other five. |
| Deployed detector | **YOLO11n (ONNX, CPU)**. USDA test mAP@0.5 **0.541** (previous pixel model 0.410); sunflower test mAP@0.5 **0.867** (pixel model 0.001). |
| Reproductive-structure, stage, health models | **Not trained.** 0 annotations exist. The modules remain labelled heuristics. |
| Tests | CI run 41764626714 on `ef89228`: all 5 jobs passed (details in §6). |

## 2. Datasets (actual files)
| Species | USDA (boxes) | TF sunflower (boxes) | iNaturalist (species label) | **Total** | iNaturalist licences |
|---|--:|--:|--:|--:|---|
| Apple | 48 | — | 107 | **155** | CC BY 67 · CC0 34 · BY-SA 6 |
| Peach | 24 | — | 71 | **95** | CC BY 55 · CC0 10 · BY-SA 6 |
| Pear | 18 | — | 29 | **47** | CC BY 23 · CC0 5 · BY-SA 1 |
| Sunflower | — | 628 | 200 | **828** | CC BY 158 · CC0 35 · BY-SA 7 |
| Hibiscus | — | — | 91 | **91** | CC BY 65 · CC0 14 · BY-SA 12 |
| Tomato | — | — | 200 | **200** | CC BY 154 · CC0 26 · BY-SA 20 |
| Strawberry | — | — | 15 | **15** | CC BY 9 · CC0 5 · BY-SA 1 |
| Brinjal | — | — | 20 | **20** | CC BY 17 · CC0 1 · BY-SA 2 |
| Chilli | — | — | 28 | **28** | CC BY 17 · CC0 10 · BY-SA 1 |
| **Total** | **90** | **628** | **761** | **1,479** | |

**Boxes:** USDA 4,651 boxes derived from masks; sunflower 2,432 YOLO boxes. The 628 derived sunflower crops are counted separately and are not in the total.

**iNaturalist verification** (`download_inat_flowering.py`, run 41665738978):
* **Species:** each observation is Research Grade, or cultivated with ≥ 1 agreeing and 0 disagreeing identifications.
* **Flowering:** each observation carries the annotation "Flowers and Fruits = Flowers".
* **Licence:** checked per photo. Only CC0, CC BY and CC BY-SA are kept; iNaturalist's default CC BY-NC is excluded.
* **Files:** all 761 files exist and decode, and all 761 have a non-empty attribution line in `ATTRIBUTION.csv`.
* **Splits:** by observer; 0 observers appear in more than one split.

**Why three crops have so few images:** strawberry, brinjal and chilli have few observations that carry *both* the flowering annotation *and* an open licence. Most iNaturalist photos are CC BY-NC.

**Unusable sources (§8):** Oxford 102 could not be reached; the INESC set was rejected for unknown species and split leakage.

## 3. Models
### 3.1 Flower detector: YOLO11n (deployed)

**Training run.** GitHub Actions run 41663935349, CPU only, finished 2026-11-03 18:56 UTC, conclusion **success**:
* 97 epochs within a 4-hour cap, 800 px, from COCO-pretrained `yolo11n.pt`
* `best.pt` chosen on validation (val mAP@0.5 0.728)
* exported to ONNX at `ai-engine/models/flower_yolo11n.onnx` (sha256 `f5e05cf8…af0b3`, 10.8 MB), with sidecar `flower_yolo11n.json` (imgsz 800)

**Deploy rule.** Written before training (`yolo_deploy_rule.py`): deploy only if USDA-test mAP@0.5 is at least the pixel model's, using the same evaluation code. 0.541 ≥ 0.410, so it was deployed.

**Independent test sets**, never used for training or selection:

| Test set | Model | mAP@0.5 | mAP@0.5:0.95 | Precision@0.5 | Recall@0.5 | F1@0.5 |
|---|---|--:|--:|--:|--:|--:|
| USDA apple/peach/pear (22 images, 929 flowers) | pixel (previous) | 0.410 | 0.190 | 0.169 | 0.610 | 0.265 |
| | **YOLO11n** | **0.541** | **0.277** | 0.265 | 0.746 | 0.391 |
| TF sunflower (95 images, 406 flowers) | pixel | 0.001 | 0.001 | 0.001 | 0.015 | 0.002 |
| | **YOLO11n** | **0.867** | **0.682** | 0.543 | 0.921 | 0.683 |

**Local check of the exported model.** I re-ran `evaluate_detector_on.py` with the committed ONNX file in this workspace (onnxruntime 1.29). It reproduced exactly: USDA 0.541 / 0.277, sunflower 0.867 / 0.682, with 0 images without predictions. Mean latency was 151 ms per image locally and 34 ms on the GitHub runner (pixel model 910 ms).

**End-to-end check.** The `Analyzer` loads `yolo11-onnx` by default. On a sunflower test image it gave 10 detections, 9 labelled sunflower.

**Limitations:**
* Precision on cluttered orchard scenes is still low (0.265).
* Count errors are large at the 0.05 evaluation threshold.
* Detection on the five crops without boxes is unvalidated.
* **Licence:** Ultralytics YOLO11 is AGPL-3.0 (`ai-engine/models/YOLO11_LICENSE_NOTE.md`). Deleting the `.onnx` restores the MIT pixel model.

### 3.2 Species recognition: open-set gallery (deployed)
Built by `build_species_gallery_multi.py`; report in `reports/species_multi_evaluation.json`.
* **Embedding:** chosen on validation by macro-F1. ImageNet MobileNetV3-Large features (`mnv3l-v1`, ONNX, BSD-3 weights, not fine-tuned) scored 0.586; the hand-crafted `hcd-v1` scored 0.442. Threshold 0.6375.
* **Gate** (fixed in advance): ≥ 50 references and validation recall and precision ≥ 0.50.
  * **Enabled:** apple, peach, pear, sunflower, hibiscus, tomato.
  * **Not enabled:** strawberry (10 references), brinjal (15), chilli (25).
* **Test** (used once): accuracy **0.746**, macro-F1 **0.727**.

| Class | Precision | Recall | F1 | Test support |
|---|--:|--:|--:|--:|
| apple | 0.722 | 0.948 | 0.820 | 403 |
| peach | 0.695 | 0.892 | 0.781 | 158 |
| pear | 0.757 | 0.848 | 0.800 | 165 |
| sunflower | 0.958 | 0.906 | 0.931 | 127 |
| tomato | 0.906 | 0.853 | 0.879 | 34 |
| hibiscus | 0.714 | 0.714 | 0.714 | **7** (very small) |
| unknown (background) | 0.524 | **0.098** | 0.165 | 224 |

Confusion matrix (rows = truth; columns apple, hibiscus, peach, pear, sunflower, tomato, unknown):

```
apple      382   0   7   9   0   1   4
hibiscus     0   5   1   0   1   0   0
peach        2   0 141   7   2   0   6
pear        20   0   5 140   0   0   0
sunflower    1   2   1   0 115   2   6
tomato       0   0   0   0   1  29   4
unknown    124   0  48  29   1   0  22
```

**By source:**

| Test set | Images | Accuracy |
|---|--:|--:|
| USDA orchard crops | 694 | 0.927 |
| iNaturalist field photos | 109 | 0.716 |
| Sunflower close-ups | 95 | 0.968 |
| USDA background (rejected as unknown) | 220 | **0.095** |

**Known regression:** background rejection fell from 0.468 (hcd-v1) to 0.095. Validation showed the same weakness before test was run. False detections are therefore usually given a species, so prefer **Close-up** mode for single flowers.

### 3.3 Heuristic modules (unchanged scope, honestly labelled)
* **Maturity, structures and pose:** heuristics, with no labels to validate them.
* **Health:** indicators are now grouped as discoloration, wilting, petal damage and visible abnormality. They are not validated and never name a disease.
* **Readiness:** species-specific rules using maturity, visible-region measurements and environment, with confidence and uncertainty. No biological ground truth exists.

## 4. Annotation workflow (Phase 3)
* **Schema:** `datasets/annotation/cvat_labels.json`:
  * `flower` box, with attributes species, stage (bud … senescent, plus `uncertain`), occluded, truncated and style class
  * `flower_centre` point
  * polygons for `petal`, `anther`, `stigma`, `stamen`, `pistil` and `health_issue`
* **Guidelines:** `ANNOTATION_GUIDELINES.md`, with class and stage definitions, visibility-only rules, 20 % second-annotator review, and splits by capture session.
* **Tool:** `datasets/scripts/annotation_stats.py`:
  * statistics for the committed data (`datasets/reports/annotation_statistics.md`)
  * CVAT-COCO validation
  * COCO → YOLO conversion for the flower and structure sets
  * covered by 3 unit tests
* **Current counts:** 0 annotations for every structure, centre, stage and health class. None were generated.

## 5. Integration
* **Backend:** loads the ONNX detector automatically (image size from the sidecar) and the gallery with its embedding.
* **`/analytics/model-performance`** serves `yolo11_deploy_decision`, `species_multi_evaluation` and the earlier reports.
* **Dashboard and PDF report** show the deployed YOLO11 metrics.
* **Evaluation page** shows:
  * a "Deployed detector: YOLO11n" card and a detector comparison table
  * the 9-species gating table and confusion matrix
  * the pixel model, labelled as the fallback
* **Health page** shows indicator categories. The Datasets page shows the new dataset statuses.

## 6. Tests
**CI run [41764626714](https://github.com/nvaltryek-001/pollinex-ai/actions/runs/41764626714)** on `ef89228`, the first commit with YOLO11 deployed: all 5 jobs **succeeded**.

| Job | Result |
|---|---|
| AI engine + simulator | **43 passed**: 27 engine, including the deployed-ONNX test and the gating test, plus 16 simulator |
| Backend | **24 passed** (SQLite and PostgreSQL migrations, startup) |
| Frontend unit (Vitest) | **11 passed** |
| Type-check and production build | ✅ |
| Playwright E2E, desktop + mobile, fake camera | **14 passed** |
| Docker images | ✅ |
| Windows fresh clone (`setup_windows.ps1`, `test_windows.ps1 -E2E`) | engine 43, backend 24, Vitest 11, Playwright 12 passed; 2 screenshot tests skipped by design |

Run locally in this workspace: AI engine 27 passed, simulator 16 passed, `ruff --select F,E9,PLE` clean. The docs-only commit after `ef89228` is checked by its own CI run, linked from the commit history.

## 7. Reproduce
```bash
python datasets/scripts/download_inat_flowering.py --per-species 200          # or workflow .github/workflows/inat.yml
python ai-engine/training/build_species_gallery_multi.py --save
python ai-engine/training/train_yolo11.py --combined --imgsz 800 --time 4 --device cpu   # or .github/workflows/yolo.yml
python ai-engine/training/evaluate_detector_on.py --data datasets/processed/usda_fruit_flower --split test --detector onnx:ai-engine/models/flower_yolo11n.onnx
python ai-engine/training/yolo_deploy_rule.py
```
GPU: `notebooks/train_yolo11_colab.ipynb`. It runs the same training and evaluation as the CPU workflow, with the same deploy rule, at 1280 px.

## 8. Not done / limitations (truthful)
1. **Strawberry, brinjal and chilli are not AI-supported.** They have 15, 20 and 28 openly licensed images, below the gate. More photos are needed: own photos via CVAT, or licence-compatible sources.
2. **No boxes for hibiscus, tomato, strawberry, brinjal or chilli**, so the detector is not trained or validated on them.
3. **No anther, stigma, stamen, pistil, petal, stage or health annotations**, so these modules remain heuristics.
4. **Small test sets** for hibiscus (7 iNaturalist test images) and brinjal, chilli and strawberry (1–2 each).
5. **Background rejection** of the deployed gallery is weak (0.095).
6. **Licensing:**
   * YOLO11 model: AGPL-3.0.
   * 56 iNaturalist photos are CC BY-SA, and the gallery embeddings derived from them carry that licence.
   * 20 of the 628 TF sunflower images have no per-image Flickr attribution upstream.
7. **Oxford 102 could not be reached** from the workspace or from GitHub runners.
8. **Not done:** phone camera test over HTTPS, and public deployment.
