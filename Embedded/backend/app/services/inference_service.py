from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

import joblib
import numpy as np
from fastapi import HTTPException, UploadFile

from ..core.config import Settings
from ..models.dto import InferenceResponse, MissingArea
from .feature_extractor import FeatureExtractor


class InferenceService:
  def __init__(self, settings: Settings, extractor: FeatureExtractor | None = None) -> None:
    self._settings = settings
    self._extractor = extractor or FeatureExtractor()

  async def run(self, upload: UploadFile) -> InferenceResponse:
    model_path = self._settings.artifacts_dir / "model.joblib"
    if not model_path.exists():
      raise HTTPException(status_code=400, detail="Chưa có model được train")

    contents = await upload.read()
    if not contents:
      raise HTTPException(status_code=400, detail="File rỗng")

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename or 'img').suffix) as tmp:
      tmp.write(contents)
      temp_path = Path(tmp.name)

    try:
      features = self._extractor.extract(temp_path).reshape(1, -1)
    finally:
      if temp_path.exists():
        temp_path.unlink()

    model = joblib.load(model_path)
    probabilities = model.predict_proba(features)[0]
    defective_prob = float(probabilities[1])
    is_defective = defective_prob >= 0.5

    missing_areas: List[MissingArea] = []
    if is_defective:
      missing_areas.append(
        MissingArea(
          id="region-1",
          description="Cụm linh kiện góc phải",
          confidence=round(defective_prob, 3),
        )
      )

    return InferenceResponse(
      isDefective=is_defective,
      confidence=round(defective_prob if is_defective else 1 - defective_prob, 3),
      timestamp=datetime.utcnow(),
      missingAreas=missing_areas,
      notes="Kết quả demo logistic regression",
    )
