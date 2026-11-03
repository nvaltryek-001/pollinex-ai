#!/usr/bin/env python3
"""Download + verify + audit the TensorFlow Flower Detection Dataset (Zenodo 7768292, CC BY 4.0, INESC TEC).

    python datasets/scripts/download_tf_flower_detection.py                      # audit only
    python datasets/scripts/download_tf_flower_detection.py --export-class 3 --species sunflower

* MD5-verified download, zip-slip guard, decode check of every image, exact-duplicate removal (SHA-1),
  per-class box counts, any class-name files shipped in the archive, and one crop contact sheet per class id
  (datasets/reports/tf_flower_detection_class_<id>.jpg) so class ids are mapped to names by LOOKING, not guessing.
* --export-class writes a YOLO subset (only images that contain that class; other classes dropped) with a
  group-free random 70/15/15 split (each source photo appears once; duplicates removed first) to
  datasets/processed/tf_flower_detection_<species>/ , resized to max 1280 px.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
URL = "https://zenodo.org/records/7768292/files/TensorFlowFlowerDetectionDataset.zip?download=1"
# The detection set has ONE class ("flower"). Species come from the source dataset's class folders:
FLOWER_PHOTOS = "https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz"
TF_CLASS_FOLDERS = {"sunflowers": "sunflower", "daisy": "daisy", "dandelion": "dandelion", "roses": "rose", "tulips": "tulip"}
MD5 = "bafa11ef76ca62b08b257bd3dc92e0c6"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def md5sum(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_labels(p: Path):
    rows = []
    for line in p.read_text().splitlines():
        v = line.split()
        if len(v) == 5:
            c, x, y, w, h = int(float(v[0])), *map(float, v[1:])
            rows.append((c, x, y, w, h))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "datasets" / "raw" / "tf_flower_detection")
    ap.add_argument("--export-class", type=int, default=None, help="(legacy) export one detection class id")
    ap.add_argument("--species", default=None)
    ap.add_argument("--join-flower-photos", action="store_true",
                    help="label each image with its species from the original tf flower_photos class folders")
    ap.add_argument("--export-species", default=None, help="with --join-flower-photos: e.g. sunflower")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    args.raw.mkdir(parents=True, exist_ok=True)
    zpath = args.raw / "TensorFlowFlowerDetectionDataset.zip"
    if not zpath.exists():
        print("downloading", URL)
        urllib.request.urlretrieve(URL, zpath)
    got = md5sum(zpath)
    if got != MD5:
        raise SystemExit(f"MD5 mismatch: {got} != {MD5} - refusing to use the archive")
    ext = args.raw / "extracted"
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        for m in names:
            if m.startswith("/") or ".." in Path(m).parts:
                raise SystemExit(f"unsafe path in archive: {m}")
        if not ext.exists():
            z.extractall(ext)
    meta_files = {m: (ext / m).read_text(errors="replace")[:2000] for m in names
                  if Path(m).suffix.lower() in {".yaml", ".yml", ".names", ".txt"} and "labels" not in Path(m).parts}

    imgs = sorted(p for p in ext.rglob("*") if p.suffix.lower() in IMG_EXT)
    seen, dups, corrupt, pairs = {}, [], [], []
    cls_boxes, cls_imgs = Counter(), Counter()
    no_label = 0
    for im in imgs:
        try:
            with Image.open(im) as x:
                x.load()
        except OSError:
            corrupt.append(str(im.relative_to(ext)))
            continue
        h = hashlib.sha1(im.read_bytes()).hexdigest()
        if h in seen:
            dups.append([str(seen[h].relative_to(ext)), str(im.relative_to(ext))])
            continue
        seen[h] = im
        lab = im.parent.parent / "labels" / (im.stem + ".txt")
        if not lab.exists():
            no_label += 1
            continue
        rows = read_labels(lab)
        for c in {r[0] for r in rows}:
            cls_imgs[c] += 1
        cls_boxes.update(r[0] for r in rows)
        pairs.append((im, rows))

    # crop contact sheet per class id (for human verification of the id -> name mapping)
    rep = ROOT / "datasets" / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    crops = defaultdict(list)
    for im, rows in pairs:
        for c, x, y, w, h in rows:
            if len(crops[c]) < 24:
                with Image.open(im) as I:
                    W, H = I.size
                    box = (int((x - w / 2) * W), int((y - h / 2) * H), int((x + w / 2) * W), int((y + h / 2) * H))
                    crops[c].append(ImageOps.fit(I.convert("RGB").crop(box), (96, 96)))
    for c, tiles in crops.items():
        sheet = Image.new("RGB", (96 * 8, 96 * 3), "white")
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % 8) * 96, (k // 8) * 96))
        sheet.save(rep / f"tf_flower_detection_class_{c}.jpg", quality=80)

    report = {"dataset_id": "tf_flower_detection", "source": URL, "license": "CC BY 4.0", "md5_verified": True,
              "image_files": len(imgs), "decoded_ok": len(imgs) - len(corrupt), "corrupt": corrupt,
              "exact_duplicates_removed": len(dups), "unique_images_with_labels": len(pairs),
              "unique_images_without_labels": no_label, "boxes_per_class_id": dict(sorted(cls_boxes.items())),
              "images_per_class_id": dict(sorted(cls_imgs.items())), "metadata_files_in_archive": meta_files,
              "archive_top_level": sorted({Path(m).parts[0] for m in names})[:20],
              "class_id_contact_sheets": [f"datasets/reports/tf_flower_detection_class_{c}.jpg" for c in sorted(crops)]}

    if args.join_flower_photos:
        import tarfile
        tgz = args.raw / "flower_photos.tgz"
        if not tgz.exists():
            print("downloading", FLOWER_PHOTOS)
            urllib.request.urlretrieve(FLOWER_PHOTOS, tgz)
        species_of, licence_lines = {}, {}
        with tarfile.open(tgz) as t:
            for m in t.getmembers():
                p = Path(m.name)
                if m.isfile() and p.suffix.lower() == ".jpg" and len(p.parts) >= 3 and p.parts[-2] in TF_CLASS_FOLDERS:
                    species_of[p.stem] = TF_CLASS_FOLDERS[p.parts[-2]]
                if p.name == "LICENSE.txt":
                    for line in t.extractfile(m).read().decode("utf-8", "replace").splitlines():
                        if line.strip() and " CC-BY" in line:
                            licence_lines[Path(line.split(":")[0].strip()).stem] = line.strip()
        joined = Counter(species_of.get(im.stem, "unmatched") for im, _ in pairs)
        report["flower_photos_join"] = {"source": FLOWER_PHOTOS, "matched_per_species": dict(joined),
                                        "rule": "detection image file stem == flower_photos file stem; species = its class folder"}
        print("join:", dict(joined))
        if args.export_species:
            sp = args.export_species
            sel = [(im, rows) for im, rows in pairs if species_of.get(im.stem) == sp and rows]
            random.Random(args.seed).shuffle(sel)
            n = len(sel)
            cut = {"train": sel[: int(0.7 * n)], "val": sel[int(0.7 * n): int(0.85 * n)], "test": sel[int(0.85 * n):]}
            out = ROOT / "datasets" / "processed" / f"tf_flower_detection_{sp}"
            gal = ROOT / "datasets" / "processed" / f"{sp}_gallery"
            for split, items in cut.items():
                for sub in ("images", "labels"):
                    (out / split / sub).mkdir(parents=True, exist_ok=True)
                for im, rows in items:
                    with Image.open(im) as I:
                        I = ImageOps.exif_transpose(I).convert("RGB")
                        I.thumbnail((1280, 1280))
                        I.save(out / split / "images" / f"{im.stem}.jpg", quality=90)
                        # largest box -> one species-gallery crop (train/val -> references, test -> held-out)
                        W, H = I.size
                        _, x, y, w, h = max(rows, key=lambda r: r[3] * r[4])
                        crop = I.crop((int((x - w / 2) * W), int((y - h / 2) * H), int((x + w / 2) * W), int((y + h / 2) * H)))
                        gd = gal / ("test/" + sp if split == "test" else sp)
                        gd.mkdir(parents=True, exist_ok=True)
                        crop.save(gd / f"{im.stem}.jpg", quality=90)
                    (out / split / "labels" / f"{im.stem}.txt").write_text(
                        "".join(f"0 {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for _, x, y, w, h in rows))
            (out / "data.yaml").write_text(f"# {sp} subset of TF Flower Detection (INESC TEC, Zenodo 7768292, CC BY 4.0); species from tf "
                                           f"flower_photos class folders\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: flower\n")
            attrib = [licence_lines[im.stem] for im, _ in sel if im.stem in licence_lines]
            (out / "LICENSE.txt").write_text(
                "Boxes: TensorFlow Flower Detection Dataset, Pinheiro, Aguiar, Figueiredo, Pinho, Valente & Santos (INESC TEC), "
                "Zenodo 7768292, CC BY 4.0.\nImages: TensorFlow flower_photos (Google), per-image Flickr licences below "
                "(all CC-BY as listed in flower_photos/LICENSE.txt). Images resized to max 1280 px.\n\n" + "\n".join(attrib) + "\n")
            report["export_species"] = {"species": sp, "images": n, "boxes": sum(len(r) for _, r in sel),
                                        "split": {k: len(v) for k, v in cut.items()}, "path": str(out.relative_to(ROOT)),
                                        "gallery_path": str(gal.relative_to(ROOT)), "per_image_licence_lines": len(attrib)}

    if args.export_class is not None:
        if not args.species:
            raise SystemExit("--species is required with --export-class")
        sel = [(im, [r for r in rows if r[0] == args.export_class]) for im, rows in pairs]
        sel = [(im, rows) for im, rows in sel if rows]
        random.Random(args.seed).shuffle(sel)
        n = len(sel)
        cut = {"train": sel[: int(0.7 * n)], "val": sel[int(0.7 * n): int(0.85 * n)], "test": sel[int(0.85 * n):]}
        out = ROOT / "datasets" / "processed" / f"tf_flower_detection_{args.species}"
        for split, items in cut.items():
            for sub in ("images", "labels"):
                (out / split / sub).mkdir(parents=True, exist_ok=True)
            for im, rows in items:
                with Image.open(im) as I:
                    I = ImageOps.exif_transpose(I).convert("RGB")
                    I.thumbnail((1280, 1280))
                    I.save(out / split / "images" / f"{im.stem}.jpg", quality=90)
                (out / split / "labels" / f"{im.stem}.txt").write_text(
                    "".join(f"0 {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for _, x, y, w, h in rows))
        (out / "data.yaml").write_text(f"# TF Flower Detection (INESC TEC, Zenodo 7768292, CC BY 4.0) - class id {args.export_class} "
                                       f"= {args.species} (verified visually)\ntrain: train/images\nval: val/images\ntest: test/images\n"
                                       f"names:\n  0: flower\n")
        (out / "LICENSE.txt").write_text("Derived from: TensorFlow Flower Detection Dataset, Pinheiro, Aguiar, Figueiredo, Pinho, "
                                         "Valente & Santos (INESC TEC), Zenodo record 7768292, CC BY 4.0 "
                                         "(https://creativecommons.org/licenses/by/4.0/). Images resized; other classes removed.\n")
        report["export"] = {"class_id": args.export_class, "species": args.species, "images": n,
                            "boxes": sum(len(r) for _, r in sel), "split": {k: len(v) for k, v in cut.items()},
                            "path": str(out.relative_to(ROOT))}
    (rep / "tf_flower_detection_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "metadata_files_in_archive"}, indent=2))
    print("metadata files:", list(meta_files))


if __name__ == "__main__":
    main()
