from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
import base64
import json

from .core.config import get_settings
from .models.dto import TrainRequest
from .services.camera_service import CameraService
from .services.dataset_service import DatasetService
from .services.inference_service import InferenceService
from .services.training_service import TrainingService

settings = get_settings()
dataset_service = DatasetService(settings)
training_service = TrainingService(settings, dataset_service)
inference_service = InferenceService(settings)

# Khởi tạo camera service
# Mặc định dùng camera index 4 (camera ngoài Brio 100)
# Có thể override qua env var CAMERA_INDEX
camera_index_env = os.getenv("CAMERA_INDEX")
if camera_index_env is not None:
  camera_index = int(camera_index_env)
else:
  # Mặc định camera index 4
  camera_index = 4
camera_service = CameraService(settings, camera_index=camera_index)

# Khởi tạo camera ngay khi server khởi động
import logging
logger = logging.getLogger(__name__)
logger.info("Đang khởi tạo camera...")
if camera_service.initialize():
  logger.info(f"Camera đã được khởi tạo thành công tại index {camera_service.camera_index}")
else:
  logger.warning(f"Không thể khởi tạo camera tại index {camera_service.camera_index}, sẽ thử lại khi có request")

app = FastAPI(title="PCB Inspector API", version="0.1.0")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_event() -> None:
  """Giải phóng camera khi server shutdown."""
  camera_service.release()


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


@app.get("/api/stream/frame")
async def get_stream_frame() -> Response:
  """Trả về frame từ video stream - ưu tiên camera ngoài, sau đó dataset, cuối cùng placeholder."""
  # Ưu tiên 1: Lấy từ camera ngoài
  frame = camera_service.get_frame()
  if frame:
    return Response(content=frame, media_type="image/jpeg")
  
  # Ưu tiên 2: Lấy từ dataset
  frame = camera_service.get_frame_from_dataset(dataset_service=dataset_service)
  if frame:
    return Response(content=frame, media_type="image/jpeg")
  
  # Fallback: Placeholder
  frame = camera_service.get_placeholder_frame()
  return Response(content=frame, media_type="image/jpeg")


@app.get("/api/stream/mjpeg")
async def get_mjpeg_stream(request: Request) -> StreamingResponse:
  """MJPEG stream endpoint - stream video mượt hơn từ camera ngoài."""
  async def generate_frames():
    try:
      while True:
        # Kiểm tra nếu client đã disconnect
        if await request.is_disconnected():
          break
        
        # Lấy frame từ camera (blocking call, nên chạy trong thread pool)
        frame = await asyncio.to_thread(camera_service.get_frame)
        
        if not frame:
          # Nếu không có frame từ camera, thử dataset
          frame = await asyncio.to_thread(
            camera_service.get_frame_from_dataset, 
            dataset_service=dataset_service
          )
        
        if not frame:
          # Fallback placeholder
          frame = await asyncio.to_thread(camera_service.get_placeholder_frame)
        
        # Format MJPEG: boundary + frame
        boundary = b"\r\n--frame\r\n"
        header = b"Content-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
        yield boundary + header + frame
        
        # Delay để giới hạn FPS (~30 FPS)
        await asyncio.sleep(1/30)
    except Exception:
      pass  # Client disconnect, ignore
  
  return StreamingResponse(
    generate_frames(),
    media_type="multipart/x-mixed-replace; boundary=frame",
    headers={
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
      "Expires": "0",
    }
  )


@app.get("/api/stream/analyze")
async def analyze_stream_frame() -> dict:
  """Phân tích frame camera hiện tại và trả về kết quả realtime."""
  frame = camera_service.get_frame()
  if not frame:
    frame = camera_service.get_frame_from_dataset(dataset_service=dataset_service)
  if not frame:
    raise HTTPException(status_code=404, detail="Không có frame camera")

  analysis = await inference_service.analyze_bytes(frame)
  return analysis.dict()


@app.websocket("/api/stream/ws")
async def websocket_stream(websocket: WebSocket):
  """WebSocket endpoint để stream video realtime - giảm độ trễ so với HTTP polling."""
  await websocket.accept()
  try:
    while True:
      # Lấy frame từ camera
      frame = await asyncio.to_thread(camera_service.get_frame)
      
      if not frame:
        # Thử dataset nếu không có camera
        frame = await asyncio.to_thread(
          camera_service.get_frame_from_dataset,
          dataset_service=dataset_service
        )
      
      if not frame:
        # Fallback placeholder
        frame = await asyncio.to_thread(camera_service.get_placeholder_frame)
      
      # Gửi frame dưới dạng base64 JSON
      frame_base64 = base64.b64encode(frame).decode('utf-8')
      message = json.dumps({
        "type": "frame",
        "data": frame_base64,
        "timestamp": asyncio.get_event_loop().time()
      })
      
      await websocket.send_text(message)
      
      # Delay để giới hạn FPS (~30 FPS)
      await asyncio.sleep(1/30)
      
  except WebSocketDisconnect:
    # Client disconnect bình thường
    pass
  except Exception as e:
    # Lỗi khác, đóng connection
    try:
      await websocket.close()
    except Exception:
      pass
