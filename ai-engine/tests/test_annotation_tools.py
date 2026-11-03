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
