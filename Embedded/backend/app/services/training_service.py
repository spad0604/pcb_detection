from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4

import cv2
import numpy as np
from ultralytics import YOLO

from ..core.config import Settings
from ..models.dto import TrainRequest, TrainingJob, BoardProfile, ComponentTemplate
from .dataset_service import DatasetService

class TrainingService:
    def __init__(self, settings: Settings, dataset_service: DatasetService) -> None:
        self._settings = settings
        self._dataset_service = dataset_service
        self._jobs: Dict[str, TrainingJob] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        
        self.model_path = settings.artifacts_dir / "best.pt"
        if not self.model_path.exists():
            print("Chưa thấy file best.pt, tải yolov8n.pt tạm thời...")
            self.model = YOLO("yolov8n.pt") 
        else:
            self.model = YOLO(str(self.model_path))

    def start_job(self, request: TrainRequest) -> str:
        job_id = uuid4().hex[:8]
        job = TrainingJob(
            jobId=job_id,
            status="running",
            progress=0.0,
            message=f"Đang phân tích layout cho {request.boardName}",
            boardName=request.boardName,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run_layout_registration, job_id, request)
        return job_id

    def get_status(self, job_id: str) -> TrainingJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_layout_registration(self, job_id: str, request: TrainRequest) -> None:
        try:
            # 1. Lấy danh sách ảnh mẫu user đã upload
            samples = self._dataset_service.list_samples()
            if not samples:
                raise ValueError("Cần ít nhất 1 ảnh chuẩn trong Dataset để học.")

            self._update_job(job_id, progress=0.2, message="Đang load ảnh mẫu...")
            
            # 2. Chọn ảnh mẫu đầu tiên làm "Golden Sample" 
            ref_sample = next((s for s in samples if s.label == 'ok'), samples[0])
            ref_path = Path(ref_sample.path)
            
            img = cv2.imread(str(ref_path))
            if img is None:
                raise ValueError(f"Không đọc được ảnh tại {ref_path}")

            self._update_job(job_id, progress=0.5, message="Đang quét linh kiện bằng YOLO...")
            
            # 3. Chạy YOLO để lấy danh sách linh kiện chuẩn
            results = self.model(img)
            components = []
            
            for r in results:
                for idx, box in enumerate(r.boxes):
                    xywhn = box.xywhn[0].tolist()
                    cls_id = int(box.cls[0])
                    # Lưu vào danh sách template
                    components.append(ComponentTemplate(
                        id=idx,
                        label=str(cls_id),
                        box=xywhn
                    ))

            if not components:
                raise ValueError("YOLO không tìm thấy linh kiện nào! Kiểm tra lại ảnh hoặc Model.")

            self._update_job(job_id, progress=0.8, message="Đang lưu Profile mạch...")
            
            # 4. Lưu dữ liệu Template
            templates_dir = self._settings.artifacts_dir / "templates"
            templates_dir.mkdir(parents=True, exist_ok=True)
            
            safe_name = "lm2596" 
            
            # A. Lưu ảnh Reference (để dùng cho thuật toán Align SIFT)
            ref_save_path = templates_dir / f"{safe_name}_ref.jpg"
            cv2.imwrite(str(ref_save_path), img)
            
            # B. Lưu JSON chứa tọa độ linh kiện
            profile = BoardProfile(
                boardName=request.boardName,
                created_at=datetime.utcnow(),
                reference_image_path=str(ref_save_path),
                components=components
            )
            json_save_path = templates_dir / f"{safe_name}.json"
            json_save_path.write_text(profile.json(), encoding="utf-8")

            # C. Set mạch này làm mặc định (Active)
            (self._settings.artifacts_dir / "active_profile.txt").write_text(safe_name, encoding="utf-8")

            self._update_job(
                job_id, 
                status="succeeded", 
                progress=1.0, 
                message=f"Đã học xong mạch '{request.boardName}'. Tìm thấy {len(components)} linh kiện.",
                metrics={"components_count": len(components)}
            )
            
            # Dọn dẹp dataset
            self._dataset_service.clear_dataset()

        except Exception as error:
            import traceback
            traceback.print_exc()
            self._update_job(job_id, status="failed", message=str(error))

    def _update_job(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                self._jobs[job_id] = job.copy(update=kwargs)