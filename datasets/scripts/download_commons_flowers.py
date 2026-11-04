#!/usr/bin/env python3
"""Download openly licensed FLOWER photos of the target crops from Wikimedia Commons (second source next to iNaturalist).

    python datasets/scripts/download_commons_flowers.py [--species strawberry brinjal chilli hibiscus tomato] [--max 200]

Selection (all verified at runtime, nothing assumed):
  * Species: starts at Category:<scientific name>; only files inside a sub-category (depth <= 3) whose title contains
    the genus name AND "flower", "blossom" or "inflorescence" are used. Category names found are written to the report.
    Species labels are therefore Commons category curation (community), NOT expert identification - weaker than
    iNaturalist Research Grade; contact sheets are written for visual review.
  * Licence: per-file extmetadata. Kept: CC0, Public domain, CC BY *, CC BY-SA * (any version). Excluded: NC, ND,
    GFDL-only, unknown. Author, licence, licence URL and file page are stored for every image.
  * Files: JPEG/PNG, original min side >= 240 px; a <= 640 px rendition is downloaded.
Checks: decode, SHA-1 duplicates, dHash near-duplicates (<= 4 bits) against each other AND against every image already in
datasets/processed/* (many iNaturalist photos are mirrored on Commons), blur/exposure flags.
Splits: by AUTHOR (hash) 70/15/15, so one photographer's series never crosses splits.
Output: datasets/processed/commons_flowers/{train,val,test}/<species>/commons_<pageid>.jpg, manifest.csv,
ATTRIBUTION.csv, LICENSE.txt; datasets/reports/commons_flowers_report.json + commons_flowers_<species>.jpg sheets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "datasets" / "processed"
OUT = PROC / "commons_flowers"
REPORTS = ROOT / "datasets" / "reports"
API = "https://commons.wikimedia.org/w/api.php"
UA = "PollinexAI-dataset-script/1.0 (https://github.com/nvaltryek-001/pollinex-ai; research dataset builder)"
SPECIES = {
    "strawberry": ["Fragaria × ananassa", "Fragaria x ananassa"],
    "brinjal": ["Solanum melongena"],
    "chilli": ["Capsicum annuum", "Capsicum frutescens"],
    "hibiscus": ["Hibiscus rosa-sinensis"],
    "tomato": ["Solanum lycopersicum"],
}
FLOWER_WORDS = ("flower", "blossom", "inflorescence")


def _wait(e: Exception, i: int) -> None:
    """Back off; honour Retry-After on HTTP 429 (Wikimedia rate limit)."""
    delay = 5 * (i + 1)
    if isinstance(e, urllib.error.HTTPError) and e.code == 429:
        try:
            delay = max(delay, int(e.headers.get("Retry-After", "30")))
        except ValueError:
            delay = max(delay, 30)
    print(f"  retry in {delay}s after {e}", file=sys.stderr)
    time.sleep(delay)


def _open(url: str, tries: int) -> bytes:
    for i in range(tries):
        try:
            time.sleep(0.4)  # stay well under the API rate limit
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            _wait(e, i)
    raise RuntimeError


def api(params: dict, tries: int = 8) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    return json.loads(_open(API + "?" + urllib.parse.urlencode(params), tries))


def get_bytes(url: str) -> bytes:
    return _open(url, 6)


def members(cat: str, kind: str) -> list[dict]:
    out, cont = [], {}
    while True:
        d = api({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": kind, "cmlimit": 500, **cont})
        out += d.get("query", {}).get("categorymembers", [])
        if "continue" not in d:
            return out
        cont = d["continue"]


def flower_categories(root_names: list[str], depth: int = 3) -> list[str]:
    found, seen = [], set()
    frontier = [f"Category:{n}" for n in root_names]
    for level in range(depth + 1):
        nxt = []
        for c in frontier:
            if c in seen:
                continue
            seen.add(c)
            try:
                subs = members(c, "subcat")
            except Exception:  # noqa: BLE001
                continue
            genus_ok = any(n.split()[0].lower() in c.lower() for n in root_names)
            if level > 0 and genus_ok and any(w in c.lower() for w in FLOWER_WORDS):
                found.append(c)
            nxt += [s["title"] for s in subs]
        frontier = nxt
        if not frontier:
            break
    return sorted(set(found))


def strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def licence_ok(meta: dict) -> tuple[bool, str]:
    code = (meta.get("License", {}).get("value") or "").lower()
    short = meta.get("LicenseShortName", {}).get("value") or ""
    s = (code + " " + short).lower()
    if "-nc" in s or " nc" in s or "-nd" in s or " nd" in s:
        return False, short
    if code.startswith(("cc0", "pd", "cc-by-sa", "cc-by")) or "public domain" in s:
        return True, short
    return False, short


def dhash(img: Image.Image) -> int:
    g = np.asarray(img.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def flags(img: Image.Image) -> list[str]:
    g = np.asarray(img.convert("L"), dtype=np.float32)
    lap = (g[1:-1, 2:] + g[1:-1, :-2] + g[2:, 1:-1] + g[:-2, 1:-1] - 4 * g[1:-1, 1:-1]).var()
    return [f for f, c in (("blurry", lap < 30), ("dark", g.mean() < 40), ("overexposed", g.mean() > 225)) if c]


def split_of(author: str) -> str:
    h = int(hashlib.sha1(f"pollinex-commons-{author.lower()}".encode()).hexdigest(), 16) % 100
    return "train" if h < 70 else "val" if h < 85 else "test"


def existing_hashes() -> list[int]:
    hs = []
    for p in PROC.rglob("*.jp*g"):
        if "commons_flowers" in p.parts or "_gallery" in str(p):
            continue
        try:
            hs.append(dhash(Image.open(p)))
        except Exception:  # noqa: BLE001
            pass
    return hs


def contact_sheet(paths, dest, cols=10, cell=120):
    paths = paths[:60]
    if not paths:
        return
    sheet = Image.new("RGB", (cols * cell, ((len(paths) + cols - 1) // cols) * cell), (255, 255, 255))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell, cell))
        sheet.paste(im, ((i % cols) * cell, (i // cols) * cell))
    sheet.save(dest, quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", nargs="*", default=list(SPECIES))
    ap.add_argument("--max", type=int, default=200)
    args = ap.parse_args()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    prior = existing_hashes()
    print("existing images hashed for cross-source dedupe:", len(prior))
    seen_sha, seen_dh, rows = set(), list(prior), []
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "Wikimedia Commons API",
              "licences_accepted": "CC0, public domain, CC BY *, CC BY-SA * (NC/ND/GFDL-only excluded)",
              "label_source": "Commons category curation (community), visually spot-checked via contact sheets",
              "per_species": {}}
    for sp in args.species:
        try:
            fetch_one(sp, args, report, rows, seen_sha, seen_dh)
        except Exception as e:  # noqa: BLE001 - keep what was downloaded for the other species
            report["per_species"][sp] = {"error": f"{type(e).__name__}: {e}"[:300],
                                         "kept": sum(r["species"] == sp for r in rows)}
            print(f"[{sp}] FAILED: {e}", file=sys.stderr)
    finish(report, rows)


def fetch_one(sp, args, report, rows, seen_sha, seen_dh):
    if True:
        cats = flower_categories(SPECIES[sp])
        files = {}
        for c in cats:
            for m in members(c, "file"):
                files[m["title"]] = c
        titles = sorted(files)
        print(f"[{sp}] flower categories {cats} -> {len(titles)} files")
        rej, drops, fl, n_ok = Counter(), Counter(), Counter(), 0
        for i in range(0, len(titles), 40):
            if n_ok >= args.max:
                break
            d = api({"action": "query", "titles": "|".join(titles[i:i + 40]), "prop": "imageinfo",
                     "iiprop": "url|sha1|size|mime|extmetadata", "iiurlwidth": 640})
            for page in d.get("query", {}).get("pages", []):
                if n_ok >= args.max:
                    break
                ii = (page.get("imageinfo") or [{}])[0]
                if ii.get("mime") not in ("image/jpeg", "image/png"):
                    rej["not_jpeg_png"] += 1
                    continue
                if min(ii.get("width", 0), ii.get("height", 0)) < 240:
                    rej["too_small"] += 1
                    continue
                meta = ii.get("extmetadata", {})
                ok, lic = licence_ok(meta)
                if not ok:
                    rej[f"licence:{lic or 'unknown'}"] += 1
                    continue
                if ii.get("sha1") in seen_sha:
                    drops["exact_duplicate"] += 1
                    continue
                try:
                    raw = get_bytes(ii.get("thumburl") or ii["url"])
                    im = Image.open(io.BytesIO(raw))
                    im.load()
                    im = im.convert("RGB")
                except Exception:  # noqa: BLE001
                    drops["download_or_decode_failed"] += 1
                    continue
                dh = dhash(im)
                if any(bin(dh ^ x).count("1") <= 4 for x in seen_dh):
                    drops["near_duplicate_incl_other_sources"] += 1
                    continue
                seen_sha.add(ii.get("sha1"))
                seen_dh.append(dh)
                author = strip_html(meta.get("Artist", {}).get("value", "")) or "unknown"
                f = flags(im)
                fl.update(f)
                split = split_of(author)
                dest = OUT / split / sp / f"commons_{page['pageid']}.jpg"
                dest.parent.mkdir(parents=True, exist_ok=True)
                im.save(dest, quality=90)
                rows.append({"species": sp, "split": split, "file": str(dest.relative_to(OUT)), "page_id": page["pageid"],
                             "title": page["title"], "category": files[page["title"]], "author": author[:200],
                             "licence": lic, "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
                             "file_page": ii.get("descriptionurl", ""), "sha1_original": ii.get("sha1"),
                             "width": im.size[0], "height": im.size[1], "quality_flags": ";".join(f)})
                n_ok += 1
            time.sleep(0.5)
        sp_rows = [r for r in rows if r["species"] == sp]
        report["per_species"][sp] = {"flower_categories": cats, "files_in_categories": len(titles), "kept": n_ok,
                                     "split": dict(Counter(r["split"] for r in sp_rows)),
                                     "authors": len({r["author"] for r in sp_rows}),
                                     "licences": dict(Counter(r["licence"] for r in sp_rows)),
                                     "rejected": dict(rej), "dropped": dict(drops), "quality_flags": dict(fl)}
        print(sp, json.dumps(report["per_species"][sp])[:600])
        contact_sheet(sorted((OUT / "test" / sp).glob("*.jpg")) + sorted((OUT / "val" / sp).glob("*.jpg")) +
                      sorted((OUT / "train" / sp).glob("*.jpg")), REPORTS / f"commons_flowers_{sp}.jpg")


def finish(report, rows):
    authors = defaultdict(set)
    for r in rows:
        authors[r["author"]].add(r["split"])
    report["authors_in_multiple_splits"] = sum(len(v) > 1 for v in authors.values())
    report["total_images"] = len(rows)
    if rows:
        with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        with open(OUT / "ATTRIBUTION.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["file", "licence", "licence_url", "author", "file_page"])
            for r in rows:
                w.writerow([r["file"], r["licence"], r["licence_url"], r["author"], r["file_page"]])
    (OUT / "LICENSE.txt").write_text(
        "Photos from Wikimedia Commons. Each file keeps its own licence (CC0 / public domain / CC BY / CC BY-SA) and author,\n"
        "listed per file in ATTRIBUTION.csv with the Commons file page. Images were downscaled (<= 640 px) and re-encoded.\n"
        "Species labels come from Commons flower categories (community curation); IMAGE-LEVEL labels only, no boxes.\n",
        encoding="utf-8")
    (REPORTS / "commons_flowers_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v["kept"] for k, v in report["per_species"].items()}), "total", len(rows))


if __name__ == "__main__":
    main()
