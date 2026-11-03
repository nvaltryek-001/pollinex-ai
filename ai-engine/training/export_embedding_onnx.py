#!/usr/bin/env python3
"""Export an ImageNet-pretrained MobileNetV3-Large feature extractor to ONNX (no fine-tuning, no project data).

    pip install torch torchvision onnx && python ai-engine/training/export_embedding_onnx.py

Output: ai-engine/models/embed_mnv3l.onnx  (input 1x3x224x224 float32, ImageNet-normalised RGB; output 1x960, pooled
features before the classifier). Weights: torchvision MobileNet_V3_Large_Weights.IMAGENET1K_V2 (torchvision, BSD-3-Clause).
Used by pollinex_ai.species as embedding 'mnv3l-v1' for the open-set reference gallery.
"""
import hashlib
import json
from pathlib import Path

import torch
import torchvision

ENGINE = Path(__file__).resolve().parents[1]


class Features(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.features, self.pool = m.features, m.avgpool

    def forward(self, x):
        return torch.flatten(self.pool(self.features(x)), 1)


def main():
    w = torchvision.models.MobileNet_V3_Large_Weights.IMAGENET1K_V2
    model = Features(torchvision.models.mobilenet_v3_large(weights=w)).eval()
    out = ENGINE / "models" / "embed_mnv3l.onnx"
    torch.onnx.export(model, torch.zeros(1, 3, 224, 224), str(out), input_names=["image"], output_names=["embedding"],
                      opset_version=17, dynamic_axes={"image": {0: "n"}, "embedding": {0: "n"}}, dynamo=False)
    meta = {"weights": str(w), "source": "torchvision", "licence": "BSD-3-Clause (torchvision)", "input": [1, 3, 224, 224],
            "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225], "dim": 960, "torch": torch.__version__,
            "torchvision": torchvision.__version__, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2), out.stat().st_size)


if __name__ == "__main__":
    main()
