from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import numpy as np
from ..core.config import Settings
from ..models.dto import TrainRequest, TrainingJob
from .dataset_service import DatasetService
from ..utils.image_processing import preprocess_image_from_path


class TrainingService:
  TEMPLATE_SIZE = (512, 512)

  def __init__(self, settings: Settings, dataset_service: DatasetService) -> None:
    self._settings = settings
    self._dataset_service = dataset_service
    self._jobs: Dict[str, TrainingJob] = {}
    self._executor = ThreadPoolExecutor(max_workers=1)
    self._lock = threading.Lock()

  def start_job(self, request: TrainRequest) -> str:
    job_id = uuid4().hex[:8]
    job = TrainingJob(
      jobId=job_id,
      status="running",
      progress=0.05,
      message=f"Đang chuẩn bị dữ liệu cho {request.boardName}",
      metrics=None,
      boardName=request.boardName,
    )
    with self._lock:
      self._jobs[job_id] = job
    self._executor.submit(self._run_training, job_id, request)
    return job_id

  def get_status(self, job_id: str) -> Optional[TrainingJob]:
    with self._lock:
      return self._jobs.get(job_id)

  def _run_training(self, job_id: str, request: TrainRequest) -> None:
    try:
      samples = self._dataset_service.list_samples()
      if len(samples) < 3:
        raise ValueError("Cần ít nhất 3 ảnh chuẩn (đủ linh kiện) để học template")

      self._update_job(job_id, progress=0.25, message="Đang chuẩn hoá ảnh")
      processed = []
      valid_paths: list[Path] = []
      for sample in samples:
        path = Path(sample.path)
        if not path.exists():
          continue
        image = self._load_image(path)
        if image is not None:
          processed.append(image)
          valid_paths.append(path)

      if not processed:
        raise ValueError("Không đọc được ảnh nào trong dataset")

      stack = np.stack(processed, axis=0)
      mean_image = np.mean(stack, axis=0)
      std_image = np.std(stack, axis=0)

      self._update_job(job_id, progress=0.75, message="Đang ghi template")
      artifact_dir = self._settings.artifacts_dir
      artifact_dir.mkdir(parents=True, exist_ok=True)
      template_path = artifact_dir / "template_model.npz"
      np.savez_compressed(
        template_path,
        mean=mean_image,
        std=std_image,
      )

      meta = {
        "boardName": request.boardName,
        "trainedAt": datetime.utcnow().isoformat(),
        "numSamples": len(processed),
        "templateSize": {"width": self.TEMPLATE_SIZE[0], "height": self.TEMPLATE_SIZE[1]},
        "sourceImages": [str(p) for p in valid_paths],
      }
      (artifact_dir / "template_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
      )

      self._update_job(
        job_id,
        status="succeeded",
        progress=1.0,
        message=f"Hoàn tất xây template PCB '{request.boardName}'",
        metrics={
          "board": request.boardName,
          "samples": len(processed),
        },
      )
      # Xóa dataset để chuẩn bị cho lần train PCB mới
      self._dataset_service.clear_dataset()
    except Exception as error:  # pragma: no cover - surfaced to client
      self._update_job(
        job_id,
        status="failed",
        message=str(error),
      )

  def _update_job(self, job_id: str, **kwargs) -> None:
    with self._lock:
      job = self._jobs.get(job_id)
      if not job:
        return
      updated = job.copy(update=kwargs)
      self._jobs[job_id] = updated

  def _load_image(self, path: Path) -> np.ndarray | None:
    return preprocess_image_from_path(path, self.TEMPLATE_SIZE)
