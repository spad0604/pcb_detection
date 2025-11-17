from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4
import shutil

from fastapi import HTTPException, UploadFile

from ..core.config import Settings
from ..models.dto import DatasetItem


class DatasetService:
  def __init__(self, settings: Settings) -> None:
    self._settings = settings
    self._dataset_dir = settings.data_dir / "dataset"
    self._meta_path = settings.data_dir / "dataset.json"
    self._dataset_dir.mkdir(parents=True, exist_ok=True)
    if not self._meta_path.exists():
      self._meta_path.write_text("[]", encoding="utf-8")

  def list_samples(self) -> List[DatasetItem]:
    data = json.loads(self._meta_path.read_text(encoding="utf-8"))
    return [DatasetItem(**item) for item in data]

  def clear_dataset(self) -> None:
    """Xóa toàn bộ dataset và metadata sau khi train."""
    if self._dataset_dir.exists():
      shutil.rmtree(self._dataset_dir)
    self._dataset_dir.mkdir(parents=True, exist_ok=True)
    self._meta_path.write_text("[]", encoding="utf-8")

  async def add_sample(self, label: str, upload: UploadFile) -> DatasetItem:
    extension = Path(upload.filename or "sample").suffix.lower()
    if extension not in self._settings.allowed_extensions:
      raise HTTPException(status_code=400, detail="File ảnh không hợp lệ")

    contents = await upload.read()
    if not contents:
      raise HTTPException(status_code=400, detail="File rỗng")

    sample_id = uuid4().hex[:8]
    timestamp = datetime.utcnow()
    target_dir = self._dataset_dir / label
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{sample_id}_{upload.filename}"
    target_path.write_bytes(contents)

    record = DatasetItem(
      id=sample_id,
      name=upload.filename or "sample",
      label=label,
      sizeBytes=len(contents),
      createdAt=timestamp,
      path=str(target_path),
    )
    data = self.list_samples()
    data.append(record)
    # Sử dụng model_dump với mode='json' để serialize datetime đúng cách
    self._meta_path.write_text(
      json.dumps([item.model_dump(mode='json') for item in data], ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
    return record
