#!/usr/bin/env python3
"""Collect and verify the POLLINEX research paper set via OpenAlex (runs in .github/workflows/papers.yml).

    python research/scripts/collect_papers.py --out research/papers --pdf-dir papers_pdf

* Recent work (2023+): OpenAlex search queries per topic, top results by relevance, de-duplicated.
* Baselines: fixed DOIs (detectors, backbones, open-set recognition, datasets used by Pollinex).
Every entry is taken from OpenAlex (title, authors, year, venue, publisher, DOI, citation count, open-access status, licence,
best OA PDF URL) - nothing is typed from memory. A PDF is downloaded ONLY when the paper's open-access location carries a
Creative Commons / public-domain licence (verbatim redistribution allowed with attribution); otherwise the entry keeps its
DOI / landing page link only (paywalled IEEE / Springer / Elsevier papers, arXiv papers under arXiv's own licence).
Outputs: <out>/papers_manifest.json, <out>/papers_manifest.csv, <out>/README.md; PDFs in --pdf-dir.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.openalex.org"
UA = "PollinexAI-research-collector/1.0 (+https://github.com/nvaltryek-001/pollinex-ai)"

TOPICS = {  # topic -> (OpenAlex search query, number to keep)
    "robotic_pollination": ("robotic pollination robot", 7),
    "pollination_review": ("artificial pollination technologies review", 4),
    "flower_detection_pollination": ("flower detection pollination deep learning", 6),
    "tomato_flower": ("tomato flower detection deep learning", 4),
    "kiwifruit_flower": ("kiwifruit flower detection pollination", 3),
    "strawberry_flower": ("strawberry flower detection deep learning", 3),
    "apple_flower": ("apple flower detection deep learning", 4),
    "stigma_anther": ("stigma anther detection flower deep learning", 3),
    "flower_pose": ("flower pose estimation pollination", 2),
    "flower_stage": ("flower blooming stage classification deep learning", 3),
    "date_palm_pepper": ("pepper OR date palm pollination robot", 2),
}
BASELINES = {  # DOI -> why it matters for Pollinex
    "10.1109/CVPR.2016.91": "YOLO v1 - one-stage detector family used for the deployed YOLO11 model",
    "10.1109/TPAMI.2016.2577031": "Faster R-CNN - two-stage detection baseline",
    "10.1109/ICCV.2017.322": "Mask R-CNN - instance segmentation baseline",
    "10.1109/ICCV.2017.324": "Focal loss / RetinaNet - dense detection baseline",
    "10.1109/CVPR.2016.90": "ResNet - standard backbone",
    "10.1109/ICCV.2019.00140": "MobileNetV3 - embedding backbone of the species gallery",
    "10.48550/arXiv.2010.11929": "Vision Transformer (ViT)",
    "10.1007/978-3-030-58452-8_13": "DETR - transformer detection",
    "10.1109/CVPR52733.2024.01605": "RT-DETR - real-time transformer detector",
    "10.48550/arXiv.2410.17725": "YOLO11 architecture overview",
    "10.1109/ICCV51070.2023.00371": "Segment Anything (SAM) - foundation segmentation",
    "10.1109/TPAMI.2012.256": "Open set recognition - basis of the 'unknown' handling",
    "10.1007/978-3-319-10602-1_48": "MS COCO - pre-training data and evaluation protocol (mAP)",
    "10.1109/LRA.2018.2849498": "Dias et al. 2018 - multi-species fruit flower detection (USDA dataset used by Pollinex)",
    "10.1109/ICVGIP.2008.47": "Oxford 102 flowers - flower classification dataset",
    "10.1371/journal.pone.0302958": "Schouten et al. 2024 - data-centric wildflower detection",
}
CC = re.compile(r"^(cc-by|cc0|public-domain|pd)", re.I)


def get(url: str, tries: int = 5, binary: bool = False):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return (data, r.headers.get("Content-Type", "")) if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410) or i == tries - 1:
                raise
            time.sleep(int(e.headers.get("Retry-After", "5")) if e.code == 429 else 3 * (i + 1))
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))
    raise RuntimeError


def abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


def record(w: dict, topic: str, why: str = "") -> dict:
    loc = w.get("best_oa_location") or {}
    src = (w.get("primary_location") or {}).get("source") or {}
    return {"openalex_id": w["id"].rsplit("/", 1)[-1], "title": w.get("title") or w.get("display_name"),
            "year": w.get("publication_year"), "date": w.get("publication_date"),
            "authors": ", ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])[:8]) +
                       (" et al." if len(w.get("authorships") or []) > 8 else ""),
            "venue": src.get("display_name"), "publisher": src.get("host_organization_name"), "type": w.get("type"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""), "cited_by": w.get("cited_by_count"),
            "is_oa": (w.get("open_access") or {}).get("is_oa"), "oa_status": (w.get("open_access") or {}).get("oa_status"),
            "licence": loc.get("license"), "pdf_url": loc.get("pdf_url"), "landing_page": loc.get("landing_page_url"),
            "topic": topic, "why": why, "abstract": abstract(w.get("abstract_inverted_index"))[:1200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("research/papers"))
    ap.add_argument("--pdf-dir", type=Path, default=Path("papers_pdf"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    papers, seen = [], set()
    for topic, (q, n) in TOPICS.items():
        params = {"search": q, "filter": "from_publication_date:2023-01-01,type:article|review",
                  "per-page": 25, "select": "id,doi,title,display_name,publication_year,publication_date,authorships,"
                  "primary_location,best_oa_location,open_access,cited_by_count,type,abstract_inverted_index"}
        res = get(f"{API}/works?" + urllib.parse.urlencode(params)).get("results", [])
        kept = 0
        for w in res:
            key = (w.get("doi") or w["id"]).lower()
            if key in seen or not w.get("title"):
                continue
            seen.add(key)
            papers.append(record(w, topic))
            kept += 1
            if kept >= n:
                break
        print(f"{topic}: kept {kept} of {len(res)}")
        time.sleep(0.3)
    for doi, why in BASELINES.items():
        try:
            w = get(f"{API}/works/https://doi.org/{doi}")
        except Exception as e:  # noqa: BLE001
            print("baseline not found in OpenAlex:", doi, e, file=sys.stderr)
            continue
        key = (w.get("doi") or w["id"]).lower()
        if key in seen:
            continue
        seen.add(key)
        papers.append(record(w, "baseline", why))
        time.sleep(0.2)
    for p in papers:  # PDFs only for CC / public-domain open-access copies
        p["pdf_file"] = None
        lic = p.get("licence") or ""
        if p.get("pdf_url") and CC.match(lic):
            slug = re.sub(r"[^A-Za-z0-9]+", "_", (p["title"] or "paper"))[:70].strip("_")
            fname = f"{p['year']}_{slug}.pdf"
            try:
                data, ctype = get(p["pdf_url"], tries=3, binary=True)
                if data[:4] == b"%PDF":
                    (args.pdf_dir / fname).write_bytes(data)
                    p["pdf_file"] = fname
                else:
                    p["pdf_error"] = f"not a PDF ({ctype})"
            except Exception as e:  # noqa: BLE001
                p["pdf_error"] = str(e)[:150]
        elif p.get("pdf_url"):
            p["pdf_error"] = f"not redistributed: licence '{lic or 'unknown'}'"
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "OpenAlex API",
            "papers": len(papers), "pdfs": sum(bool(p["pdf_file"]) for p in papers)}
    (args.out / "papers_manifest.json").write_text(json.dumps({"meta": meta, "papers": papers}, indent=2, ensure_ascii=False))
    cols = ["topic", "year", "title", "authors", "venue", "publisher", "doi", "cited_by", "oa_status", "licence", "pdf_file",
            "landing_page", "why"]
    with open(args.out / "papers_manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(papers)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
