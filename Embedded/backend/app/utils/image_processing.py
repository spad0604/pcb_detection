from __future__ import annotations
import io
import cv2
import numpy as np
from PIL import Image

def preprocess_image_from_path(path: Path, size: tuple[int, int] | None = None) -> np.ndarray | None:
  """Đọc ảnh từ đường dẫn, trả về numpy array (BGR)."""
  try:
    img = cv2.imread(str(path))
    if img is None:
        return None
    return img
  except Exception:
    return None

def preprocess_image_from_bytes(data: bytes, size: tuple[int, int] | None = None) -> np.ndarray | None:
  """Đọc ảnh từ bytes (stream)."""
  try:
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img
  except Exception:
    return None