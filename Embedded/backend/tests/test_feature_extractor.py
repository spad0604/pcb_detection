from pathlib import Path

import numpy as np
from PIL import Image

from app.services.feature_extractor import FeatureExtractor


def test_feature_vector_shape(tmp_path: Path) -> None:
  image_path = tmp_path / "pcb.png"
  pixels = np.zeros((32, 32, 3), dtype=np.uint8)
  pixels[:, :16, :] = 255
  Image.fromarray(pixels).save(image_path)

  extractor = FeatureExtractor()
  vector = extractor.extract(image_path)

  assert vector.shape == (5,)
  assert np.all(vector >= 0)
  assert np.all(vector <= 1)
