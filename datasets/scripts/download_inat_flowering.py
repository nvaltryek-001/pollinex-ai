#!/usr/bin/env python3
"""Download openly licensed, species-verified FLOWERING photos from iNaturalist for the nine target crops.

    python datasets/scripts/download_inat_flowering.py --per-species 200 [--species hibiscus tomato ...]

Source and verification (all checked by this script, nothing assumed):
  * Taxon: resolved by exact scientific name via /v1/taxa; observations are requested by taxon_id, so every
    observation's taxon is the target species or a descendant (cultivar/variety). The returned taxon is re-checked.
  * Species identification: kept only if the observation is Research Grade (community agreement) OR is a
    cultivated/captive observation (Casual only because cultivated) with >= 1 independent agreeing
    identification and 0 disagreements. Cultivated crops are rarely Research Grade, hence the second rule.
  * Phenology: annotation "Flowers and Fruits = Flowers" (formerly "Plant Phenology = Flowering"; term ids
    verified against /v1/controlled_terms at runtime).
  * Licence: per PHOTO licence code must be cc0 or cc-by (filtered by the API and re-checked per photo).
    Attribution string, photographer login, observation URL and licence are stored for every image.
  * One photo per observation (the first openly licensed one), at most --max-per-user observations per observer.
Image checks: decode, min side, SHA-1 exact duplicates, dHash near-duplicates (dropped, across all species/splits),
blur / exposure flags (kept but flagged).
Splits: by OBSERVER (hash of user id -> 70/15/15) so one person's photos of the same plant never cross splits.

Output: datasets/processed/inat_flowering/{train,val,test}/<species>/inat_<obs>_<photo>.jpg (medium size, <= 500 px)
        manifest.csv, ATTRIBUTION.csv, LICENSE.txt, ../../reports/inat_flowering_report.json, contact sheets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "datasets" / "processed" / "inat_flowering"
REPORTS = ROOT / "datasets" / "reports"
API = "https://api.inaturalist.org/v1"
UA = "PollinexAI-dataset-script/1.0 (+https://github.com/nvaltryek-001/pollinex-ai)"
SPECIES = {  # project id -> exact iNaturalist scientific name
    "hibiscus": "Hibiscus rosa-sinensis",
    "tomato": "Solanum lycopersicum",
    "strawberry": "Fragaria × ananassa",
    "brinjal": "Solanum melongena",
    "chilli": "Capsicum annuum",
    "sunflower": "Helianthus annuus",
    "apple": "Malus domestica",
    "peach": "Prunus persica",
    "pear": "Pyrus communis",
}
OPEN_LICENCES = {"cc0", "cc-by"}


def get_json(url: str, tries: int = 4) -> dict:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"  retry {i + 1} after {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise RuntimeError("unreachable")


def get_bytes(url: str, tries: int = 3) -> bytes:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))
    raise RuntimeError("unreachable")


def verify_terms() -> tuple[int, int]:
    seen = []
    for url in (f"{API}/controlled_terms", f"{API}/controlled_terms/for_taxon?taxon_id=47126"):  # 47126 = Plantae
        data = get_json(url)
        for t in data.get("results", []):
            tl = t.get("label") or (t.get("labels") or [{}])[0].get("label", "")
            vals = [(v.get("id"), v.get("label") or (v.get("labels") or [{}])[0].get("label", "")) for v in t.get("values", [])]
            seen.append((t.get("id"), tl, vals))
            if str(tl).lower() in ("plant phenology", "flowers and fruits"):  # renamed by iNaturalist
                for vid, vl in vals:
                    if str(vl).lower() in ("flowering", "flowers"):
                        return t["id"], vid
    raise SystemExit(f"could not find the flowering annotation in controlled terms; got {json.dumps(seen)[:3000]}")


def resolve_taxon(name: str) -> dict:
    data = get_json(f"{API}/taxa?" + urllib.parse.urlencode({"q": name, "is_active": "true", "per_page": 30}))
    norm = lambda s: s.replace("×", "x").replace(" x ", " ").replace("  ", " ").strip().lower()  # noqa: E731
    for t in data["results"]:
        if norm(t["name"]) == norm(name):
            return t
    raise SystemExit(f"taxon '{name}' not found exactly; candidates: {[t['name'] for t in data['results'][:8]]}")


def identification_ok(obs: dict) -> tuple[bool, str]:
    if obs.get("quality_grade") == "research":
        return True, "research_grade"
    agree = obs.get("num_identification_agreements") or 0
    disagree = obs.get("num_identification_disagreements") or 0
    if obs.get("captive") and agree >= 1 and disagree == 0:
        return True, "cultivated_with_agreement"
    return False, ""


def taxon_ok(obs: dict, taxon_id: int) -> bool:
    t = obs.get("taxon") or {}
    return t.get("id") == taxon_id or taxon_id in (t.get("ancestor_ids") or [])


def dhash(img: Image.Image) -> int:
    g = np.asarray(img.convert("L").resize((9, 8), Image.BILINEAR), dtype=np.int16)
    bits = (g[:, 1:] > g[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def quality_flags(img: Image.Image) -> list[str]:
    g = np.asarray(img.convert("L"), dtype=np.float32)
    flags = []
    lap = (g[1:-1, 2:] + g[1:-1, :-2] + g[2:, 1:-1] + g[:-2, 1:-1] - 4 * g[1:-1, 1:-1]).var()
    if lap < 30:
        flags.append("blurry")
    if g.mean() < 40:
        flags.append("dark")
    if g.mean() > 225:
        flags.append("overexposed")
    return flags


def split_of(user_id: int) -> str:
    h = int(hashlib.sha1(f"pollinex-inat-{user_id}".encode()).hexdigest(), 16) % 100
    return "train" if h < 70 else "val" if h < 85 else "test"


def fetch_species(sp: str, name: str, term: tuple[int, int], n: int, max_per_user: int) -> tuple[list[dict], Counter]:
    taxon = resolve_taxon(name)
    print(f"[{sp}] taxon {taxon['id']} {taxon['name']} ({taxon.get('rank')})")
    rejected = Counter()
    kept, per_user, id_below = [], Counter(), None
    for _page in range(40):
        q = {"taxon_id": taxon["id"], "term_id": term[0], "term_value_id": term[1], "photos": "true",
             "photo_license": ",".join(sorted(OPEN_LICENCES)), "quality_grade": "research,casual",
             "per_page": 200, "order_by": "id", "order": "desc"}
        if id_below:
            q["id_below"] = id_below
        data = get_json(f"{API}/observations?" + urllib.parse.urlencode(q))
        res = data.get("results", [])
        if not res:
            break
        for o in res:
            id_below = o["id"]
            ok, how = identification_ok(o)
            if not ok:
                rejected["identification_not_verified"] += 1
                continue
            if not taxon_ok(o, taxon["id"]):
                rejected["taxon_mismatch"] += 1
                continue
            uid = (o.get("user") or {}).get("id")
            if uid is None or per_user[uid] >= max_per_user:
                rejected["per_user_cap"] += 1
                continue
            photo = next((p for p in o.get("photos", []) if (p.get("license_code") or "").lower() in OPEN_LICENCES), None)
            if photo is None:
                rejected["no_open_photo"] += 1
                continue
            per_user[uid] += 1
            kept.append({"species": sp, "scientific_name": (o.get("taxon") or {}).get("name"), "taxon_id": taxon["id"],
                         "obs_id": o["id"], "photo_id": photo["id"], "user_id": uid,
                         "user_login": (o.get("user") or {}).get("login"), "observed_on": o.get("observed_on"),
                         "place_guess": o.get("place_guess"), "identification": how,
                         "quality_grade": o.get("quality_grade"), "captive": bool(o.get("captive")),
                         "licence": photo["license_code"].lower(), "attribution": photo.get("attribution"),
                         "photo_url": photo["url"].replace("/square.", "/medium."),
                         "obs_url": f"https://www.inaturalist.org/observations/{o['id']}"})
            if len(kept) >= int(n * 1.25):  # head-room for decode/duplicate drops
                return kept, rejected
        time.sleep(1.1)  # iNaturalist asks for <= ~1 request/second
    return kept, rejected


def contact_sheet(paths: list[Path], dest: Path, cols: int = 10, cell: int = 120) -> None:
    paths = paths[:60]
    if not paths:
        return
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell, cell))
        sheet.paste(im, ((i % cols) * cell, (i // cols) * cell))
    sheet.save(dest, quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", nargs="*", default=list(SPECIES))
    ap.add_argument("--per-species", type=int, default=200)
    ap.add_argument("--max-per-user", type=int, default=5)
    ap.add_argument("--min-side", type=int, default=240)
    args = ap.parse_args()
    term = verify_terms()
    print("phenology term verified:", term)
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    seen_sha, seen_dh, rows = {}, [], []
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "iNaturalist API v1 (api.inaturalist.org)",
              "phenology_term": {"term_id": term[0], "value_id": term[1], "meaning": "Flowers and Fruits = Flowers (formerly Plant Phenology = Flowering)"},
              "licences_accepted": sorted(OPEN_LICENCES), "per_species": {}}
    for sp in args.species:
        cands, rejected = fetch_species(sp, SPECIES[sp], term, args.per_species, args.max_per_user)
        drops, flags_c, n_ok = Counter(), Counter(), 0
        for c in cands:
            if n_ok >= args.per_species:
                break
            try:
                raw = get_bytes(c["photo_url"])
                im = Image.open(io.BytesIO(raw))
                im.load()
                im = im.convert("RGB")
            except Exception:  # noqa: BLE001
                drops["download_or_decode_failed"] += 1
                continue
            if min(im.size) < args.min_side:
                drops["too_small"] += 1
                continue
            sha = hashlib.sha1(raw).hexdigest()
            if sha in seen_sha:
                drops["exact_duplicate"] += 1
                continue
            dh = dhash(im)
            if any(bin(dh ^ d).count("1") <= 4 for d in seen_dh):
                drops["near_duplicate_dhash<=4"] += 1
                continue
            seen_sha[sha] = 1
            seen_dh.append(dh)
            flags = quality_flags(im)
            flags_c.update(flags)
            split = split_of(c["user_id"])
            dest = OUT / split / sp / f"inat_{c['obs_id']}_{c['photo_id']}.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            rows.append({**c, "split": split, "file": str(dest.relative_to(OUT)), "sha1": sha, "width": im.size[0],
                         "height": im.size[1], "quality_flags": ";".join(flags)})
            n_ok += 1
            time.sleep(0.25)
        sp_rows = [r for r in rows if r["species"] == sp]
        report["per_species"][sp] = {
            "scientific_name": SPECIES[sp], "candidates": len(cands), "kept": n_ok,
            "split": dict(Counter(r["split"] for r in sp_rows)), "observers": len({r["user_id"] for r in sp_rows}),
            "identification": dict(Counter(r["identification"] for r in sp_rows)),
            "licences": dict(Counter(r["licence"] for r in sp_rows)), "rejected_observations": dict(rejected),
            "dropped_images": dict(drops), "quality_flags": dict(flags_c)}
        print(sp, json.dumps(report["per_species"][sp]))
        contact_sheet(sorted((OUT / "test" / sp).glob("*.jpg")) + sorted((OUT / "train" / sp).glob("*.jpg")),
                      REPORTS / f"inat_flowering_{sp}.jpg")
    # leakage check: no observer in two splits
    users = defaultdict(set)
    for r in rows:
        users[r["user_id"]].add(r["split"])
    report["observers_in_multiple_splits"] = sum(len(v) > 1 for v in users.values())
    report["total_images"] = len(rows)
    fields = list(rows[0].keys()) if rows else []
    with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(OUT / "ATTRIBUTION.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "licence", "attribution", "observation_url"])
        for r in rows:
            w.writerow([r["file"], r["licence"], r["attribution"], r["obs_url"]])
    (OUT / "LICENSE.txt").write_text(
        "Photos from iNaturalist (https://www.inaturalist.org). Each photo keeps its own licence (CC0 1.0 or CC BY 4.0)\n"
        "and attribution, listed per file in ATTRIBUTION.csv. Images are unmodified 'medium' renditions (<= 500 px).\n"
        "Species labels come from iNaturalist identifications (see manifest.csv 'identification'); these are\n"
        "IMAGE-LEVEL species labels only - there are NO bounding boxes or structure annotations in this set.\n", encoding="utf-8")
    (REPORTS / "inat_flowering_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["kept"] for k, v in report["per_species"].items()}), "total", len(rows),
          "observers in >1 split:", report["observers_in_multiple_splits"])


if __name__ == "__main__":
    main()
