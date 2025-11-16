from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from PIL import Image

from ..models.dto import DatasetItem


class FeatureExtractor:
  def extract(self, path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    array = np.asarray(image, dtype=np.float32) / 255.0
    mean_rgb = array.mean(axis=(0, 1))
    std_rgb = array.std()
    gray = array.mean(axis=2)
    contrast = gray.std()
    return np.array([*mean_rgb, std_rgb, contrast], dtype=np.float32)

  def build_dataset(self, samples: Iterable[DatasetItem]) -> Tuple[np.ndarray, np.ndarray]:
    features = []
    labels = []
    for sample in samples:
      path = Path(sample.path)
      if not path.exists():
        continue
      try:
        vector = self.extract(path)
      except Exception:
        continue
      features.append(vector)
      labels.append(1 if sample.label == "missing" else 0)
    if not features:
      return np.empty((0, 5)), np.empty((0,))
    return np.vstack(features), np.array(labels)
