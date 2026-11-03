# Contributing

1. Fork, create a branch, run `scripts/setup_dev.sh`.
2. Keep the provenance contract: every new AI output must carry a `method` field (`trained_model`, `heuristic`, `rule_engine`,
   `simulation`, …) and the UI must show it with `MethodBadge`.
3. Never add hard-coded or placeholder metrics, fake detections or invented datasets. New metrics must come from a script that
   writes a report under `ai-engine/reports/`.
4. Tune on validation, evaluate test once; document any deviation.
5. Add tests (`pytest`, `vitest`, or Playwright) and run `scripts/run_tests.sh` before opening a PR.
6. Do not commit datasets, secrets or large weights; add download scripts and manifest entries instead.
7. Knowledge-base edits need an `evidence` key and an honest `evidence_level`.

Style: Python — type hints, small pure functions in `ai-engine`/`simulation`, no web code there. TypeScript — strict mode,
functional components, data only via `lib/api.ts`.
