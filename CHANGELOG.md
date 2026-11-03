# Changelog

## [1.0.0] - 2026-11-02
### Milestones
- **M1** Research foundation: literature review, comparison, gaps, methodology, references; architecture.
- **M2** Dataset ingestion: USDA fruit-flower preparation, leakage-safe splits, upstream box-orientation audit, manifest of 10 sources, download scripts, CVAT workflow.
- **M3** Detection & classification: CPU pixel detector (test mAP50 0.410), baseline + ablation, speed/accuracy study; open-set species gallery.
- **M4** Structure & maturity: labelled heuristics for centre region, stage, health, pose.
- **M5** Pollination intelligence: 9-species knowledge base, explainable readiness rules, environmental factors.
- **M6** Virtual simulation: seeded particle engine, sweeps, Three.js/2-D replay.
- **M7** Web application: FastAPI backend (auth, scans, live WS, records, analytics, reports, admin) and React app (20 pages).
- **M8** Testing: 35 executed engine/simulation tests; backend, Vitest and Playwright suites written.
- **M9** Deployment & docs: Docker, Compose, Render, Vercel, CI, 11 docs.
- **M10** Final audit (docs/FINAL_PROJECT_REPORT.md).

### Known gaps
YOLO11 not trained; web stack not yet built/executed against its dependencies; no public deployment.
