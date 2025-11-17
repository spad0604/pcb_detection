from __future__ import annotations

import io
import tempfile
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile
from PIL import Image

from ..core.config import Settings
from ..models.dto import BoundingBox, InferenceResponse, MissingArea


class InferenceService:
  def __init__(self, settings: Settings) -> None:
    self._settings = settings

  async def run(self, upload: UploadFile) -> InferenceResponse:
    contents = await upload.read()
    if not contents:
      raise HTTPException(status_code=400, detail="File rỗng")

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename or 'img').suffix) as tmp:
      tmp.write(contents)
      temp_path = Path(tmp.name)

    try:
      return await self.analyze_image(temp_path)
    finally:
      if temp_path.exists():
        temp_path.unlink()

  async def analyze_image(self, path: Path) -> InferenceResponse:
    template = self._load_template()
    candidate = self._load_image(path, size=template["size"])
    if candidate is None:
      raise HTTPException(status_code=400, detail="Không xử lý được ảnh đầu vào")
    return self._evaluate(candidate, template)

  async def analyze_bytes(self, data: bytes) -> InferenceResponse:
    template = self._load_template()
    candidate = self._load_image_from_bytes(data, size=template["size"])
    if candidate is None:
      raise HTTPException(status_code=400, detail="Không xử lý được frame camera")
    return self._evaluate(candidate, template)

  def _load_template(self) -> Dict:
    template_path = self._settings.artifacts_dir / "template_model.npz"
    meta_path = self._settings.artifacts_dir / "template_meta.json"
    if not template_path.exists() or not meta_path.exists():
      raise HTTPException(
        status_code=400,
        detail="Chưa có template cho PCB. Vui lòng train với ảnh chuẩn (đủ linh kiện) trước khi inference.",
      )

    with np.load(template_path) as template_npz:
      mean_image = template_npz["mean"]
      std_image = template_npz["std"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    target_size = (mean_image.shape[1], mean_image.shape[0])
    return {
      "mean": mean_image,
      "std": std_image,
      "size": target_size,
      "boardName": meta.get("boardName", "N/A"),
    }

  def _load_image(self, path: Path, size: tuple[int, int]) -> np.ndarray | None:
    try:
      with Image.open(path) as img:
        img = img.convert("L")
        img = img.resize(size, Image.BILINEAR)
        return np.asarray(img, dtype=np.float32) / 255.0
    except Exception:
      return None

  def _load_image_from_bytes(self, data: bytes, size: tuple[int, int]) -> np.ndarray | None:
    try:
      with Image.open(io.BytesIO(data)) as img:
        img = img.convert("L")
        img = img.resize(size, Image.BILINEAR)
        return np.asarray(img, dtype=np.float32) / 255.0
    except Exception:
      return None

  def _evaluate(self, candidate: np.ndarray, template: Dict) -> InferenceResponse:
    compare_result = self._compare(candidate, template["mean"], template["std"])
    missing_areas = self._build_missing_areas(compare_result["mask"])
    anomaly_ratio = compare_result["anomaly_ratio"]
    is_defective = anomaly_ratio >= 0.01
    confidence = float(min(0.99, max(0.01, anomaly_ratio * 8)))
    notes = f"PCB: {template['boardName']} · Sai lệch {anomaly_ratio * 100:.2f}%"

    return InferenceResponse(
      isDefective=is_defective,
      confidence=round(confidence, 3),
      timestamp=datetime.utcnow(),
      missingAreas=missing_areas,
      notes=notes,
    )

  def _compare(self, image: np.ndarray, template_mean: np.ndarray, template_std: np.ndarray) -> dict:
    diff = np.abs(image - template_mean)
    adaptive_threshold = np.maximum(template_std * 1.5, 0.05)
    mask = diff > adaptive_threshold
    mask = mask.astype(np.uint8) * 255
    mask = cv2.medianBlur(mask, 5)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    anomaly_ratio = float(mask.mean() / 255.0)
    return {"mask": mask, "anomaly_ratio": anomaly_ratio}

  def _build_missing_areas(self, mask: np.ndarray) -> List[MissingArea]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape[:2]
    surface = float(h * w)
    areas: List[MissingArea] = []

    for idx, contour in enumerate(contours):
      x, y, cw, ch = cv2.boundingRect(contour)
      area = cw * ch
      if area < 200:
        continue
      area_ratio = area / surface
      confidence = min(0.99, max(0.05, area_ratio * 10))
      bbox = BoundingBox(
        x=float(x / w),
        y=float(y / h),
        width=float(cw / w),
        height=float(ch / h),
      )
      areas.append(
        MissingArea(
          id=f"region-{idx + 1}",
          description=f"Vùng lệch ({int(x)}, {int(y)}) kích thước {cw}x{ch}",
          confidence=round(confidence, 3),
          bbox=bbox,
        )
      )
    return areas[:5]

