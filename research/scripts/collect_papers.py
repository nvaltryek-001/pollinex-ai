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

# topic -> (OpenAlex search, title gate regex (must match, case-insensitive), number to keep)
TOPICS = {
    "robotic_pollination": ("pollination robot", r"pollinat.*(robot|drone|uav|autonom|end-effector|manipulator|machine)|(robot|drone|uav|autonom).*pollinat", 10),
    "pollination_review": ("artificial pollination review", r"pollinat.*(review|survey|advance|progress)|(review|survey|advance|progress).*pollinat", 4),
    "flower_detection": ("flower detection deep learning orchard", r"flower.*(detect|recogni|segment|count)|(detect|recogni|segment|count).*flower", 6),
    "tomato_flower": ("tomato flower detection", r"tomato.*(flower|blossom|pollinat)", 3),
    "kiwifruit_flower": ("kiwifruit flower detection", r"(kiwi|actinidia).*(flower|pollinat)", 3),
    "strawberry_flower": ("strawberry flower detection", r"strawberr.*(flower|bloom|pollinat)", 2),
    "apple_flower": ("apple flower detection", r"apple.*(flower|blossom|bloom)", 3),
    "pepper_flower": ("pepper chili flower detection", r"(pepper|chil).*(flower|pollinat)", 2),
    "stigma_anther": ("stigma anther pistil detection deep learning", r"(stigma|anther|pistil|stamen).*(detect|segment|recogni|locat|deep|network)", 3),
    "flower_pose": ("flower pose orientation estimation", r"flower.*(pose|orientation)", 2),
    "flower_stage": ("flowering stage detection deep learning", r"(bloom|flower).*(stage|phenolog)", 3),
    "flower_dataset": ("flower image dataset detection", r"flower.*dataset|dataset.*flower", 2),
}
EXCLUDE_TITLE = re.compile(r"pollination algorithm|flower pollination optimi|rumor|drowning|battery|diagnos", re.I)
ALREADY_IN_DRIVE = [  # papers the user already placed in the Drive folder (matched by title, not re-uploaded)
    "chilli pepper flower detection approach based on yolov8", "yo-afd", "tomato flowers and buds in greenhouses on 3p2r",
    "vm-yolo", "actinidia flower detection and gender", "yolo11-araf", "grapevine inflorescence segmentation",
    "time-lapse camera monitoring of insects", "monitoring of bees through object recognition",
    "automated flower species detection and classification", "floral classification revolution",
    "automated flower species recognition using deep learning",
]
BASELINES = {  # DOI -> why it matters for Pollinex
    "10.1109/CVPR.2016.91": "YOLO v1 - one-stage detector family used for the deployed YOLO11 model",
    "10.1109/CVPR52729.2023.00721": "YOLOv7 - trainable bag-of-freebies YOLO baseline",
    "10.48550/arXiv.2405.14458": "YOLOv10 - NMS-free real-time detection",
    "10.48550/arXiv.2410.17725": "YOLO11 architecture overview (deployed detector family)",
    "10.1109/TPAMI.2016.2577031": "Faster R-CNN - two-stage detection baseline",
    "10.1109/ICCV.2017.322": "Mask R-CNN - instance segmentation baseline",
    "10.1109/ICCV.2017.324": "Focal loss / RetinaNet - dense detection baseline",
    "10.1109/CVPR42600.2020.01079": "EfficientDet - scalable detection baseline",
    "10.1007/978-3-030-58452-8_13": "DETR - transformer detection",
    "10.1109/CVPR52733.2024.01605": "RT-DETR - real-time transformer detector",
    "10.1109/CVPR.2016.90": "ResNet - standard backbone",
    "10.1109/ICCV.2019.00140": "MobileNetV3 - embedding backbone of the species gallery",
    "10.48550/arXiv.2010.11929": "Vision Transformer (ViT)",
    "10.48550/arXiv.2304.07193": "DINOv2 - self-supervised visual features (open-set embeddings)",
    "10.1109/ICCV51070.2023.00371": "Segment Anything (SAM) - foundation segmentation",
    "10.1109/TPAMI.2012.256": "Open set recognition - basis of the 'unknown' handling",
    "10.1007/978-3-319-10602-1_48": "MS COCO - pre-training data and evaluation protocol (mAP)",
    "10.1109/LRA.2018.2849498": "Dias et al. 2018 - multi-species fruit flower detection (USDA dataset used by Pollinex)",
    "10.1109/ICVGIP.2008.47": "Oxford 102 flowers - flower classification dataset",
    "10.1109/IROS60139.2025.11247634": "FloPE - flower pose estimation for precision pollination",
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


def pdf_candidates(w: dict) -> list[tuple[str, str]]:
    """(url, licence) for every open-access location with a CC / PD licence, plus publisher PDF patterns."""
    out = []
    for loc in [w.get("best_oa_location") or {}] + (w.get("locations") or []):
        lic = loc.get("license") or ""
        if CC.match(lic):
            if loc.get("pdf_url"):
                out.append((loc["pdf_url"], lic))
            lp, doi = loc.get("landing_page_url") or "", (w.get("doi") or "").replace("https://doi.org/", "")
            if "mdpi.com" in lp:
                out.append((lp.rstrip("/") + "/pdf", lic))
            if doi.startswith("10.3389/"):
                out.append((f"https://www.frontiersin.org/articles/{doi}/pdf", lic))
            if doi.startswith("10.1038/s41598"):
                out.append((f"https://www.nature.com/articles/{doi.split('/', 1)[1]}.pdf", lic))
            if doi.startswith("10.1371/"):
                out.append((f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable", lic))
            if doi.startswith("10.1186/") and "biomedcentral.com" in lp:
                host = lp.split("/")[2]
                out.append((f"https://{host}/counter/pdf/{doi}", lic))
            if doi.lower().startswith("10.48550/arxiv."):
                out.append((f"https://arxiv.org/pdf/{doi.split('.', 2)[2]}", lic))
    seen, uniq = set(), []
    for u, lic in out:
        if u not in seen:
            seen.add(u)
            uniq.append((u, lic))
    return uniq


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
            "pdf_candidates": pdf_candidates(w), "topic": topic, "why": why, "abstract": abstract(w.get("abstract_inverted_index"))[:1200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("research/papers"))
    ap.add_argument("--pdf-dir", type=Path, default=Path("papers_pdf"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    papers, seen = [], set()
    for topic, (q, gate, n) in TOPICS.items():
        params = {"search": q, "filter": "from_publication_date:2023-01-01,type:article|review",
                  "per-page": 50, "select": "id,doi,title,display_name,publication_year,publication_date,authorships,"
                  "primary_location,best_oa_location,locations,open_access,cited_by_count,type,abstract_inverted_index"}
        res = get(f"{API}/works?" + urllib.parse.urlencode(params)).get("results", [])
        kept = 0
        for w in res:
            key = (w.get("doi") or w["id"]).lower()
            t = (w.get("title") or "")
            if key in seen or not t or not re.search(gate, t, re.I) or EXCLUDE_TITLE.search(t):
                continue
            if any(x in t.lower() for x in ALREADY_IN_DRIVE):
                print("  already in Drive:", t[:80])
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
            w = get(f"{API}/works/https://doi.org/{doi}?select=id,doi,title,display_name,publication_year,publication_date,"
                    "authorships,primary_location,best_oa_location,locations,open_access,cited_by_count,type,abstract_inverted_index")
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
        p["pdf_file"], errs = None, []
        slug = re.sub(r"[^A-Za-z0-9]+", "_", (p["title"] or "paper"))[:70].strip("_")
        for url, lic in p.pop("pdf_candidates"):
            try:
                data, ctype = get(url, tries=2, binary=True)
            except Exception as e:  # noqa: BLE001
                errs.append(f"{url}: {str(e)[:80]}")
                continue
            if data[:4] == b"%PDF":
                fname = f"{p['year']}_{slug}.pdf"
                (args.pdf_dir / fname).write_bytes(data)
                p.update(pdf_file=fname, pdf_source=url, licence=p.get("licence") or lic)
                break
            errs.append(f"{url}: not a PDF ({ctype[:40]})")
        if not p["pdf_file"]:
            p["pdf_note"] = "; ".join(errs)[:300] if errs else f"no CC-licensed open-access copy (licence: {p.get('licence') or 'none'})"
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "OpenAlex API",
            "papers": len(papers), "pdfs": sum(bool(p["pdf_file"]) for p in papers)}
    (args.out / "papers_manifest.json").write_text(json.dumps({"meta": meta, "papers": papers}, indent=2, ensure_ascii=False))
    cols = ["topic", "year", "title", "authors", "venue", "publisher", "doi", "cited_by", "oa_status", "licence", "pdf_file",
            "landing_page", "why", "pdf_note"]
    with open(args.out / "papers_manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(papers)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
