# POLLINEX AI — Literature Review

_Last updated: 2026-11-02. Prepared before architecture design (Milestone M1)._

## How this review was produced (and its limits)

Bibliographic details below were checked against publisher / repository landing pages on 2026-11-02.
Where a detail could not be confirmed it is marked **[unverified]** rather than guessed.
Some full texts were behind access controls (ScienceDirect returned a client error, PMC served a CAPTCHA),
so a few summaries rely on abstracts, accepted manuscripts or preprints of the same work. This is stated per entry.

Evidence types are labelled:

| Label | Meaning |
|---|---|
| **PR** | Peer-reviewed journal / conference paper |
| **PP** | Preprint (not peer-reviewed in that form) |
| **DS** | Dataset documentation |
| **SW** | Software / tooling documentation |
| **OURS** | A method proposed by this project (not validated by an external publication) |

Numerical results quoted below are **the authors' reported results**. POLLINEX AI does **not** claim to reproduce or achieve them. Our own measured results live in `ai-engine/reports/` and `docs/AI_MODEL_DOCUMENTATION.md`.

---

## 1. FloPE: Flower Pose Estimation for Precision Pollination  — PR (also PP)

| Field | Detail |
|---|---|
| Authors | Rashik Shrestha, Madhav Rijal, Trevor Smith, Yu Gu |
| Year | 2025 (arXiv v1: 8 Mar 2025; v2: 30 Jul 2025) |
| Venue | IEEE/RSJ IROS 2025 (inferred from DOI prefix `IROS60139.2025`) |
| DOI / URL | 10.1109/IROS60139.2025.11247634 · https://arxiv.org/abs/2503.11692 |
| Source read | arXiv abstract page |

- **Problem.** Robotic pollination requires the 6-DoF pose of fragile flowers in cluttered clusters; manually annotating flower pose is expensive.
- **Methodology.** Photorealistic synthetic training data rendered from **3D Gaussian Splatting** reconstructions, giving exact pose labels "for free"; **teacher→student knowledge distillation** to obtain a lightweight real-time estimator.
- **Dataset.** Synthetic (3DGS-rendered) with pose annotations; size/composition not stated on the abstract page.
- **Architecture.** High-capacity teacher, lightweight student (exact layers not described in the abstract).
- **Reported results.** Mean pose error ≈ 0.6 cm and 19.14°; up to 78.75 % pollination success on single- and multi-arm robots.
- **Limitations (our reading).** Requires 3D capture + robot calibration; results are on specific flowers/robots; synthetic-to-real gap not quantified in the abstract.
- **Relevance.** Defines what "flower pose" means for pollination: a flower **centre** plus a **facing direction**, not just a bounding box.
- **What we adapt.** (a) A pose-lite module that outputs flower centre, image-space orientation estimate and an alignment vector from a virtual effector; (b) the principle that pose must be labelled as **image-space only** without depth/calibration. We do **not** implement 3DGS or 6-DoF pose.

## 2. Artificial Pollination Technologies: A Review — PR

| Field | Detail |
|---|---|
| Authors | Melissa A. Broussard, Michael Coates, Paul Martinsen |
| Year / Venue | 2023, *Agronomy* 13(5):1351 |
| DOI | 10.3390/agronomy13051351 |
| Source read | MDPI full text |

- **Problem.** Survey of how pollen is collected, stored and applied by humans and machines.
- **Methodology.** Narrative review grouping applicators: hand, hand-held/backpack, vehicle-mounted, UAV, robotic; dry vs. wet application; pollen sourcing and storage.
- **Key findings (reported).** Artificial pollination is mostly *supplementary*; for tomato (self-compatible) vibration can release pollen without an external pollen supply; pollen supply is a major bottleneck; broadcast methods waste most pollen; environmental factors (temperature, humidity, flower age) are often ignored in trials; efficacy data are scarce and usually limited to fruit/seed set.
- **Relevance.** Directly motivates our **species-specific strategy table** (vibration for tomato/brinjal vs. compatible-pollen cross-transfer for apple/pear) and our **environmental context** module.
- **What we adapt.** Strategy categories and the explicit separation between *pollen delivery* (simulated) and *fruit set* (not measured by us).

## 3. A Comprehensive Review of Autonomous Flower Pollination Techniques: Progress, Challenges, and Future Directions — PR

| Field | Detail |
|---|---|
| Authors | Q. Zhang, Z. Zhang, S. H. Manzoor, T. Li, C. Igathinathane, W. Li, M. Zhang, M. Mhamed, S. M. Javidan, M. A. Abdelhamid |
| Year / Venue | 2025, *Computers and Electronics in Agriculture* (issued 1 Oct 2025; volume/article no. **[unverified]**) |
| DOI | 10.1016/j.compag.2025.110577 |
| Source read | Abstract (institutional repository); ScienceDirect full text was not reachable |

- **Problem / scope.** Bibliometric + technical review of ground-robot and UAV pollination; topics: flower identification & localisation, path planning, pollination mechanisms.
- **Findings (abstract-level).** Field is early-stage with relatively few publications, mainly from the USA and China, moving from concept to practice.
- **Relevance.** Confirms the perception pipeline we implement: *detect → localise → plan approach*. Our "approach guidance" is a software analogue of the localisation→path-planning stage.

## 4. A Comprehensive Review of Current Robot-Based Pollinators for Crop Pollination — PR

| Field | Detail |
|---|---|
| Authors | Rajmeet Singh, Lakmal Seneviratne, Irfan Hussain |
| Year / Venue | *Artificial Intelligence Review* 59(1): article 26; online 25 Nov 2025 (cover date 2026) |
| DOI | 10.1007/s10462-025-11409-1 (preprint: arXiv 2410.23747) |
| Source read | Springer landing page |

- **Scope.** Greenhouse robot pollinators; tomato ≈ 60 % of studies, kiwifruit ≈ 25 %, plus strawberry, bramble, date palm, watermelon.
- **Mechanisms.** Air-jet, water-jet, linear actuator / contact, ultrasonic, air-liquid spray; perception with RGB-D, deep detectors for tomato flowers and buds, binocular cameras, visual servoing.
- **Reported numbers (other authors' systems).** e.g. tomato vibration pollinators operating near 150–200 Hz.
- **Limitations noted.** Crop-specific designs, little demonstrated autonomy, foliage occlusion and motion blur for drones, many lab-only tests.
- **What we adapt.** Mechanism taxonomy for the knowledge base (`vibration`, `contact_transfer`, `air_assisted`, `spray`), and the vibration-frequency parameter in the tomato/brinjal **simulation profile** (labelled as a literature-derived parameter, not a validated setting).

## 5. Data-Centric AI Approach for Automated Wildflower Monitoring — PR (+PP, +DS)

| Field | Detail |
|---|---|
| Authors | Gerard Schouten, Bas S. H. T. Michielsen, Barbara Gravendeel |
| Year / Venue | 2024, *PLOS ONE* 19(9) |
| DOI | 10.1371/journal.pone.0302958 · preprint 10.1101/2024.04.18.590040 · dataset 10.34894/U4VQJ6 |
| Source read | bioRxiv full-text preprint |

- **Problem.** Counting wildflowers from overview images (not single close-ups).
- **Dataset (EWD).** 2,002 images (~30 MP) of ~1 m² plots, 160 species, 65,571 boxes, long-tailed; **CC BY-NC 4.0** on DataverseNL.
- **Model.** Faster R-CNN, ResNet-50 backbone (TorchVision), transfer learning.
- **Reported results.** mAP@0.5 = 0.82 over a balanced 49-species subset; AP per species 0.99 → 0.19; complex inflorescences hardest.
- **Data-centric techniques.** Botanically defined floral count units; 7 annotation rules; 4-eyes QC; **resolution-preserving tiling** that avoids cutting objects; stratified balancing.
- **Limitations.** Partial objects at tile borders; only 49/160 species modelled; look-alike confusion; no spatial/phenological context; not yet field-validated.
- **What we adapt.** (a) **Tiling** for our high-resolution orchard images (AppleA is 5184×3456); (b) written annotation guidelines in `datasets/annotation/ANNOTATION_GUIDELINES.md`; (c) a group-aware split rule; (d) open-set handling so unseen species are not forced into a known class.

## 6. DoPI: The Database of Pollinator Interactions — PR (data paper) / DS

| Field | Detail |
|---|---|
| Authors | Nicholas J. Balfour, Maria Clara Castellanos, Dave Goulson, Andrew Philippides, Chris Johnson |
| Year / Venue | 2022, *Ecology* (ESA Data Paper; volume/article no. **[unverified]**) |
| URL | https://www.dopi.org.uk/ · PMC9786240 |
| Source read | Author-hosted PDF (University of Sussex) |

- **Content.** ~100k records and ~320–330k interactions (the paper reports both 101,539 and 100,721 records in different sections), 1,888 pollinator and 1,241 plant species; **Great Britain only**; compiled from 302 publications (1802–2019), unpublished datasets and a journal archive.
- **Licence.** No formal open licence named; "copyright restrictions: none", citation requested.
- **Limitations.** Geographic and seasonal bias, under-representation of beetles, moths and trees.
- **Relevance.** The knowledge base has a `pollinator_groups` field per species. DoPI can enrich it, but because DoPI is GB-only it **cannot** be assumed to represent Indian field conditions for tomato, brinjal or chilli. We ship an importer stub and document this geographic gap rather than importing GB data as if it were universal.

---

## 7. Supporting technical literature

| Topic | Reference | Type | How it informs POLLINEX |
|---|---|---|---|
| Fruit-flower detection | Dias, Tabb, Medeiros, "Multispecies Fruit Flower Detection Using a Refined Semantic Segmentation Network", *IEEE RA-L* 3(4):3003–3010, 2018, doi:10.1109/LRA.2018.2849498 | PR | Source paper of the **dataset we actually train on** (apple / peach / pear). Their approach is segmentation-first, which motivates our segmentation→instance pipeline. |
| One-stage detection | Redmon et al., "You Only Look Once", CVPR 2016, doi:10.1109/CVPR.2016.91 | PR | Basis of the YOLO family; our deep-detector training recipe targets YOLO11. |
| YOLO11 | Jocher & Qiu, *Ultralytics YOLO11* (software, 2024), AGPL-3.0 | SW | Chosen deep detector (licence implications documented in `docs/AI_MODEL_DOCUMENTATION.md`). |
| Real-time DETR | Zhao et al., "DETRs Beat YOLOs on Real-time Object Detection", CVPR 2024, arXiv:2304.08069 | PR | Considered; rejected for laptop CPU training budget. |
| Instance segmentation | He et al., "Mask R-CNN", ICCV 2017, doi:10.1109/ICCV.2017.322 | PR | Reference architecture for reproductive-structure masks once annotations exist. |
| Superpixels | Achanta et al., "SLIC Superpixels Compared to State-of-the-Art Superpixel Methods", IEEE TPAMI 34(11), 2012, doi:10.1109/TPAMI.2012.120 | PR | Region unit used by our CPU baseline flower segmenter. |
| Fine-grained flowers | Nilsback & Zisserman, "Automated Flower Classification over a Large Number of Classes", ICVGIP 2008, doi:10.1109/ICVGIP.2008.47 | PR/DS | Oxford-102 contains *sunflower* and *hibiscus* classes; used as an optional reference-gallery source via download script. |

## 8. Pollination biology used in the knowledge base

Species rules in `backend/app/knowledge/species_kb.json` use well-established horticultural knowledge
(e.g. tomato and brinjal have poricidal anthers that release pollen under vibration; apple and pear cultivars are
largely self-incompatible and need compatible cross-pollen; sunflower florets are protandrous and open centripetally).
Each entry lists its evidence source and an explicit `evidence_level`:

- `review` – stated in one of the reviews above;
- `textbook` – standard horticultural knowledge, not tied to one paper; **should be verified against local
  extension-service guidance before agronomic use**.

No species rule in POLLINEX has been validated by our own field experiment.
