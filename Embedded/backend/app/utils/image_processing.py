from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# HSV range cho màu xanh dương (băng tải)
BLUE_LOWER = np.array([90, 40, 40], dtype=np.uint8)
BLUE_UPPER = np.array([140, 255, 255], dtype=np.uint8)


def _build_component_mask(bgr_image: np.ndarray) -> np.ndarray:
  """Tạo mask cho vùng linh kiện (loại bỏ nền xanh dương)."""
  hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
  blue_mask = cv2.inRange(hsv, BLUE_LOWER, BLUE_UPPER)
  component_mask = cv2.bitwise_not(blue_mask)
  component_mask = cv2.medianBlur(component_mask, 5)
  kernel = np.ones((5, 5), np.uint8)
  component_mask = cv2.morphologyEx(component_mask, cv2.MORPH_OPEN, kernel)
  component_mask = cv2.morphologyEx(component_mask, cv2.MORPH_DILATE, kernel)

  # Nếu mask quá nhỏ (có thể do ánh sáng), fallback dùng toàn bộ ảnh
  coverage = component_mask.mean() / 255.0
  if coverage < 0.05:
    component_mask = np.ones_like(component_mask, dtype=np.uint8) * 255
  return component_mask


def _preprocess_pil_image(image: Image.Image, size: tuple[int, int]) -> np.ndarray:
  """Tiền xử lý ảnh PIL -> grayscale float32 [0,1], loại nền xanh."""
  image = image.convert("RGB")
  rgb_array = np.asarray(image)
  if rgb_array.ndim != 3:
    rgb_array = np.stack([rgb_array] * 3, axis=-1)

  bgr = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
  mask = _build_component_mask(bgr)
  gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

  masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
  resized_gray = cv2.resize(masked_gray, size, interpolation=cv2.INTER_LINEAR)
  resized_mask = cv2.resize(mask, size, interpolation=cv2.INTER_NEAREST)

  normalized = resized_gray.astype(np.float32) / 255.0
  normalized_mask = (resized_mask > 0).astype(np.float32)

  processed = normalized * normalized_mask
  return processed


def preprocess_image_from_path(path: Path, size: tuple[int, int]) -> np.ndarray | None:
  """Đọc và tiền xử lý ảnh từ path."""
  try:
    with Image.open(path) as img:
      return _preprocess_pil_image(img, size)
  except Exception:
    return None


def preprocess_image_from_bytes(data: bytes, size: tuple[int, int]) -> np.ndarray | None:
  """Đọc và tiền xử lý ảnh từ bytes (camera/video)."""
  try:
    with Image.open(io.BytesIO(data)) as img:
      return _preprocess_pil_image(img, size)
  except Exception:
    return None

