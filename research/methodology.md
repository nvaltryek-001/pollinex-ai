# Experimental Methodology

## 1. Questions
1. How well can a CPU-only model trained on public orchard data detect individual fruit-tree flowers? (*measured*)
2. Can an open-set reference gallery recognise species without forcing unknown flowers into known classes? (*measured, with a confound*)
3. Can species-specific pollination knowledge be turned into explainable, uncertainty-aware decision support? (*rule engine; not biologically validated*)
4. How sensitive is simulated pollen transfer to effector alignment, vibration frequency and wind? (*simulation only*)

## 2. Data
* **USDA Multi-species Fruit Flower** (Dias, Tabb & Medeiros 2018; CC BY 4.0) via its public GitHub mirror, commit `17db8b119a39`.
* 90 images with masks are usable (117 upstream images lack annotations and are excluded, not used as negatives).
* **Ground truth** = 8-connected components of the masks (area ≥ 9 px at 1600 px working size). Upstream JSON/CSV boxes were
  audited and found inconsistently oriented relative to images (vertical flip better in 50/90 images), so they are not used.
* **Splits**: per capture group (apple_A, apple_B, peach, pear_seq1, pear_seq2), images sorted by frame number and cut into
  contiguous 60/15/25 % blocks → train 54 / val 14 / test 22 images. A perceptual-hash audit found 0 near-duplicate pairs across splits.

## 3. Detector (Module 1)
* Pixel classifier: gradient-boosted trees (scikit-learn `HistGradientBoostingClassifier`) on a 36-channel feature stack
  (colour in RGB/Lab/HSV, whiteness, excess-green; Gaussian-smoothed colour, gradient magnitude, scale-normalised LoG and local
  contrast at σ = 1, 2, 4).
* Training pixels: up to 3,000 flower + 6,000 background pixels per training image, one third of negatives drawn from a 15-px
  ring around flowers (hard negatives). Seed 20261102.
* Instances: probability map → threshold → opening/hole filling → connected components (or distance-transform watershed).
* **Tuning**: threshold, minimum area and peak distance chosen by grid search on **validation mAP@0.5**.
* **Test**: evaluated once with frozen parameters; COCO-style 101-point AP at IoU 0.50 and averaged over 0.50:0.95.
* **Baseline and ablation** on the identical protocol: (A) Otsu threshold on a whiteness channel, no learning; (B) the same
  learner with the 12 per-pixel colour features only; (C) the full feature stack (deployed).
* **Inference trade-off**: resolution × classification stride evaluated on validation; selection rules fixed in advance
  (full analysis: fastest config within 0.02 val mAP50 of the best; live: fastest within 75 % of the best).

## 4. Species gallery (Module 2)
* Embedding: HSV histogram, Lab moments, centre-minus-ring colour, HOG and uniform LBP (no deep backbone - PyTorch was not
  installable in the build environment).
* kNN (k = 7) cosine vote; **open-set threshold** chosen on validation by macro-F1 over {apple, peach, pear, unknown}, where
  "unknown" queries are background crops.
* Test: open-set confusion matrix, background rejection rate, and **leave-one-species-out** (remove a species from the
  gallery and measure how often its flowers come back as `unknown`).
* **Confound:** each species was photographed with a different camera setup, so species is entangled with capture conditions.

## 5. Heuristic modules (Modules 3, 4, 6, 7)
Stage, centre-region, health and pose modules are deterministic image analyses with documented thresholds. They are
unit-tested for behaviour (e.g. brown petals raise the senescent score) but **not** evaluated for accuracy because no labelled
data exists. They are labelled `heuristic` in every API response and UI element.

## 6. Readiness engine (Module 5)
Rules map (species, stage) to a category using `ready_stages / approaching_stages / past_stages` from the knowledge base,
adjust for visible browning, and down-weight confidence when environmental readings fall outside general or species-specific
ranges. Confidence = stage score × detection score × species confidence × environment multiplier. Output is called a
*visual readiness estimate*.

## 7. Simulation
Seeded particle model (mm, s): release schedule (vibration release peaks in a 150–200 Hz band, from the reviewed robot
literature), gravity-limited settling, drag toward canopy-attenuated wind, Gaussian turbulence, guided transport for
brush/effector modes (75 % carry fraction), capture inside the stigma/target radius. Outputs: released, captured, lost,
**simulated transfer efficiency**, target coverage, alignment error. Parameter sweeps run with a fixed seed.

## 8. Reproducibility
```bash
python datasets/scripts/prepare_usda_fruit_flower.py --src <clone>
python ai-engine/training/train_detector.py          # ~25-60 min on 2 CPU cores
python ai-engine/training/evaluate_detector.py       # speed/accuracy trade-off
python ai-engine/training/train_species.py           # < 1 min
```
All seeds are fixed; reports record time, machine and parameters.

## 9. Plan for biological validation (future, requires physical trials)
Randomised complete block design per crop with three treatments — **natural**, **manual** (crop-specific method from the
knowledge base) and **app-assisted** (manual pollination timed by Pollinex readiness estimates) — on tagged flowers, ≥ 3 blocks,
≥ 30 flowers per treatment per block. Response variables: fruit set at 2–3 weeks, seed count, fruit weight and shape class
(strawberry). Record temperature/humidity per session. Analyse with a mixed model (treatment fixed, block/plant random).
The *Pollination history* page already stores the records this design needs (method, timestamp, plant, flowers treated,
observed outcome). Until such data exist, no claim is made that Pollinex improves pollination outcomes.
