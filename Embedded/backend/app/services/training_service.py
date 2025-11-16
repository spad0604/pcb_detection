from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from ..core.config import Settings
from ..models.dto import TrainRequest, TrainingJob
from .dataset_service import DatasetService
from .feature_extractor import FeatureExtractor


class TrainingService:
  def __init__(self, settings: Settings, dataset_service: DatasetService) -> None:
    self._settings = settings
    self._dataset_service = dataset_service
    self._extractor = FeatureExtractor()
    self._jobs: Dict[str, TrainingJob] = {}
    self._executor = ThreadPoolExecutor(max_workers=1)
    self._lock = threading.Lock()

  def start_job(self, request: TrainRequest) -> str:
    job_id = uuid4().hex[:8]
    job = TrainingJob(jobId=job_id, status="running", progress=0.05, message="Đang chuẩn bị dữ liệu")
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
      if len(samples) < 4:
        raise ValueError("Cần ít nhất 4 mẫu để train")

      features, labels = self._extractor.build_dataset(samples)
      if features.size == 0:
        raise ValueError("Không đọc được ảnh nào")

      self._update_job(job_id, progress=0.3, message="Đang chia dữ liệu")
      X_train, X_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=request.testSplit,
        shuffle=True,
        stratify=labels,
        random_state=42,
      )

      self._update_job(job_id, progress=0.6, message="Đang train mô hình")
      model = LogisticRegression(max_iter=request.epochs)
      model.fit(X_train, y_train)

      self._update_job(job_id, progress=0.8, message="Đang đánh giá")
      preds = model.predict(X_test)
      probas = model.predict_proba(X_test)[:, 1]
      acc = accuracy_score(y_test, preds) if len(y_test) else 0
      confidence = float(np.mean(np.maximum(probas, 1 - probas))) if len(probas) else 0

      artifact_path = self._settings.artifacts_dir / "model.joblib"
      joblib.dump(model, artifact_path)

      self._update_job(
        job_id,
        status="succeeded",
        progress=1.0,
        message=f"Hoàn tất · acc={acc:.2f}",
        metrics={"accuracy": round(acc, 3), "confidence": round(confidence, 3)},
      )
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
