"""Tests for datasets/scripts/annotation_stats.py (synthetic in-memory COCO fixture; not a dataset)."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("annotation_stats", ROOT / "datasets" / "scripts" / "annotation_stats.py")
ann = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ann)


def fixture():
    return {"categories": [{"id": 1, "name": "flower"}, {"id": 2, "name": "anther"}, {"id": 3, "name": "bogus"}],
            "images": [{"id": 1, "file_name": "sessA/a.jpg", "width": 100, "height": 50},
                       {"id": 2, "file_name": "sessB/b.jpg", "width": 100, "height": 50}],
            "annotations": [
                {"image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 10], "attributes": {"species": "tomato", "stage": "uncertain"}},
                {"image_id": 1, "category_id": 2, "bbox": [12, 12, 4, 4], "segmentation": [[1, 2, 3, 4]]},
                {"image_id": 1, "category_id": 1, "bbox": [95, 10, 20, 10], "attributes": {}}]}


def test_check_coco_reports_issues():
    rep = ann.check_coco(fixture())
    assert rep["annotations_per_class"] == {"flower": 2, "anther": 1}
    assert rep["issues"]["unknown_label:bogus"] == 1
    assert rep["issues"]["box_outside_image"] == 1
    assert rep["issues"]["polygon_with_<3_points"] == 1
    assert rep["issues"]["flower_without_species"] == 1
    assert rep["images_without_annotations"] == 1 and rep["uncertain_stage"] == 1


def test_coco_to_yolo_splits_by_session(tmp_path):
    coco_path = tmp_path / "annotations.json"
    coco_path.write_text(json.dumps(fixture()))
    written = ann.coco_to_yolo(fixture(), coco_path)
    split_a = ann.split_for("sessA")
    lab = (tmp_path / "yolo" / "labels" / split_a / "a.txt").read_text().split()
    assert lab[0] == "0" and abs(float(lab[1]) - 0.2) < 1e-6 and abs(float(lab[3]) - 0.2) < 1e-6
    assert (tmp_path / "yolo_structures" / "labels" / split_a / "a.txt").exists()
    assert sum(v for k, v in written.items() if k.startswith("yolo_structures")) == 1  # image b has no structures


def test_committed_report_never_invents_structure_labels():
    rep = ann.committed_report()
    assert all(v == 0 for v in rep["cvat_schema_class_counts"].values())


def _load(name, rel):
    s = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_import_verified_boxes_rejects_unreviewed_and_keeps_source_split(tmp_path):
    imp = _load("import_verified_boxes", "datasets/annotation/import_verified_boxes.py")
    man = ROOT / "datasets" / "processed" / "inat_flowering" / "manifest.csv"
    import csv as _csv
    rows = [r for r in _csv.DictReader(man.open(encoding="utf-8")) if r["species"] == "tomato"][:3]
    names = [f"inat_flowering/{r['file']}" for r in rows]
    coco = {"categories": [{"id": 1, "name": "flower"}],
            "images": [{"id": i + 1, "file_name": n, "width": 100, "height": 100} for i, n in enumerate(names)],
            "annotations": [
                # image 1: reviewed box -> accepted
                {"image_id": 1, "category_id": 1, "bbox": [10, 10, 30, 30], "attributes": {"species": "tomato", "verified": True}},
                # image 2: one reviewed + one untouched machine proposal -> whole image rejected
                {"image_id": 2, "category_id": 1, "bbox": [10, 10, 30, 30], "attributes": {"species": "tomato", "verified": True}},
                {"image_id": 2, "category_id": 1, "bbox": [50, 50, 20, 20], "attributes": {"species": "tomato", "verified": False}},
                # image 3: reviewed but species uncertain -> box dropped, image has no usable box
                {"image_id": 3, "category_id": 1, "bbox": [10, 10, 30, 30], "attributes": {"species": "uncertain", "verified": "true"}}]}
    f = tmp_path / "reviewed.json"
    f.write_text(json.dumps(coco))
    splits = {f"inat_flowering/{r['file']}": r["split"] for r in rows}
    items, rej = imp.import_coco([f], splits)
    assert len(items) == 1 and items[0]["split"] == rows[0]["split"]
    assert items[0]["boxes"][0][0] == imp.CID["tomato"]
    assert rej["image_has_unverified_box"] == 1 and rej["box_species_other_or_uncertain"] == 1


def test_machine_proposals_are_marked_unverified_and_import_rejects_them():
    imp = _load("import_verified_boxes2", "datasets/annotation/import_verified_boxes.py")
    p = ROOT / "datasets" / "annotation" / "proposals" / "chilli_proposals_coco.json"
    coco = json.loads(p.read_text())
    assert "UNVERIFIED" in coco["info"]["description"]
    assert coco["annotations"] and all(a["attributes"]["verified"] is False for a in coco["annotations"])
    items, rej = imp.import_coco([p], imp.load_splits())
    assert items == []  # untouched proposals never become training data


def test_species_detector_gate_blocks_training_without_verified_labels(tmp_path):
    tr = _load("train_species_detector", "ai-engine/training/train_species_detector.py")
    for split, n in (("train", 60), ("val", 20), ("test", 20)):
        d = tmp_path / split / "labels"
        d.mkdir(parents=True)
        for i in range(n):
            (d / f"{i}.txt").write_text("3 0.5 0.5 0.2 0.2\n")  # sunflower only
    g = tr.gate(tr.class_image_counts(tmp_path))
    assert not g["passed"] and "sunflower" not in g["short_classes"] and "tomato" in g["short_classes"]
    assert g["short_classes"]["tomato"]["still_needed"] == {"train": 50, "val": 15, "test": 15}
