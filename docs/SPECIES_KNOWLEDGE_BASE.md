# Species knowledge base

POLLINEX AI keeps species information as data, not in React code:

| File | Content | Used by |
|---|---|---|
| `ai-engine/pollinex_ai/knowledge/species_kb.json` | Pollination biology used by the readiness rules and the simulator: mechanism, pollination types, ready stages, strategy, limitations, evidence level | readiness engine, simulator, `/api/v1/ai/species` |
| `ai-engine/pollinex_ai/knowledge/species_botany.json` | General botany for all 9 species: family, flower, petals, visible reproductive structures, flowering, flowering period (with regional notes), pollination mechanism, pollinators, self/cross-pollination, fruit (name, type, characteristics), agricultural relevance, sources | species information panel (scan results, scan detail, Species page), per-scan PDF |

`load_kb()` in `ai-engine/pollinex_ai/knowledge/__init__.py` merges the two. `load_botany()` refuses to load if any species is
missing a required field or cites a source id that is not defined. `test_botany_knowledge_covers_all_nine_species` checks
this in CI.

## General knowledge vs. image inference

The app keeps these apart everywhere:

* **Inferred from the image:** flower boxes (YOLO11 detector), species (reference gallery, or *unknown*), developmental
  stage, centre region and visible colour anomalies (heuristics), and visual readiness (rules). Each result carries a method badge.
* **General knowledge about the species:** everything in `species_botany.json`. The panel is labelled
  *"reference knowledge · not from this image"*. It describes the species in general and appears only after the species has
  been identified, or chosen by the user.
* **Not identified by any model:** fruit, disease, pollen viability, stigma receptivity and fertilisation. The `fruit`
  entries describe what the species produces after successful pollination. They are not a detection. The file's
  `fruit_recognition` statement is shown under every panel.

## Fruit recognition: status and future workflow

No fruit dataset or model exists in this repository, so the app makes no fruit claims. To add fruit recognition later:

1. Collect licensed fruit photos per species. The iNaturalist *Flowers and Fruits = Fruits or Seeds* annotation and the
   Commons fruit categories can be used with the existing collectors in `datasets/`.
2. Keep fruit as a separate label space (`<species>_fruit`) and a separate model or gallery. Do not merge it with flower classes.
3. Use grouped train/val/test splits, the same gating rule as the flower gallery (≥ 50 references; validation precision and
   recall ≥ 0.5), and report test metrics separately from flower recognition.
4. Only then add a `fruit` result block to the pipeline, with its own method badge.

## AI support per species

Taken from the shipped gallery metadata (`species_status`):

| Species | Gallery | Support |
|---|---|---|
| apple, peach, pear, sunflower, hibiscus, tomato | enabled | validated (≥ 20 test images) |
| brinjal, chilli | enabled | limited evidence (11 and 7 test images) |
| strawberry | not enabled | not AI-supported; select it manually |

All 9 species have a full botany record whatever their AI support. The record is general knowledge and needs no model.

## Sources

The `sources` block in `species_botany.json` lists Plants of the World Online (Kew) for taxonomy, Broussard et al. (2023,
*Agronomy* 13:1351), FAO pollination resources, and Singh et al. (2025, *AI Review*). Each species cites the ones it uses.
Flowering periods are typical ranges. They vary with cultivar, latitude, altitude and season, and the text says so.
