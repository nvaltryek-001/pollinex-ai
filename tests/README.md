# tests/

Shared fixtures for backend, Playwright and manual testing. Unit/integration suites live next to their code:
`ai-engine/tests`, `simulation/tests`, `backend/tests`, `frontend/src/test`, `frontend/e2e`. Run everything with
`scripts/run_tests.sh`.

`fixtures/sample_orchard.jpg` (peach, test split image `peach_70`) and `fixtures/sample_apple.jpg` (`apple_IMG_0394`) are
resized derivatives of the USDA Multi-species Fruit Flower dataset — Dias, Tabb & Medeiros (2018),
doi:10.15482/USDA.ADC/1423466, **CC BY 4.0**. Both come from the held-out test split, so using them for demos does not leak
training data.
