# YOLO11 model licence note

`flower_yolo11n.onnx` (present only if the pre-registered deploy rule in `ai-engine/training/yolo_deploy_rule.py`
passed) was trained with Ultralytics YOLO11, which is licensed **AGPL-3.0**. Ultralytics states that models trained
with its software fall under the same licence. The rest of Pollinex (MIT) does not depend on it:
delete `flower_yolo11n.onnx` and the backend falls back to the MIT pixel detector automatically.
Training data: USDA Multi-species Fruit Flower (CC BY 4.0) and the TF Flower Detection sunflower subset (CC BY 4.0).
