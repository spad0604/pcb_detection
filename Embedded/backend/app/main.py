from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .models.dto import TrainRequest
from .services.dataset_service import DatasetService
from .services.inference_service import InferenceService
from .services.training_service import TrainingService

settings = get_settings()
dataset_service = DatasetService(settings)
training_service = TrainingService(settings, dataset_service)
inference_service = InferenceService(settings)

app = FastAPI(title="PCB Inspector API", version="0.1.0")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
  return {"status": "ok"}


@app.get("/api/dataset")
async def list_dataset() -> list[dict]:
  samples = dataset_service.list_samples()
  return [item.dict() for item in samples]


@app.post("/api/dataset")
async def upload_dataset(
  label: str = Form(..., pattern=r"^(ok|missing)$"),
  file: UploadFile = File(...),
) -> dict:
  record = await dataset_service.add_sample(label=label, upload=file)
  return record.dict()


@app.post("/api/train")
async def start_training(request: TrainRequest) -> dict[str, str]:
  job_id = training_service.start_job(request)
  return {"jobId": job_id}


@app.get("/api/train/{job_id}")
async def training_status(job_id: str) -> dict:
  status = training_service.get_status(job_id)
  if not status:
    raise HTTPException(status_code=404, detail="Không tìm thấy job")
  return status.dict()


@app.post("/api/inference")
async def run_inference(file: UploadFile = File(...)) -> dict:
  result = await inference_service.run(file)
  return result.dict()
