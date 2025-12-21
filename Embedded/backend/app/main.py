from __future__ import annotations

import asyncio
import os
import json
import logging
import base64

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .core.config import get_settings
from .services.camera_service import CameraService
from .services.inference_service import InferenceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
inference_service = InferenceService(settings)

camera_index_env = os.getenv("CAMERA_INDEX")
camera_index = int(camera_index_env) if camera_index_env is not None else 4
camera_service = CameraService(settings, camera_index=camera_index)

if camera_service.initialize():
    logger.info(f"Camera đã sẵn sàng tại index {camera_service.camera_index}")
else:
    logger.warning(f"Không mở được camera index {camera_service.camera_index}")

app = FastAPI(title="PCB Inspector API (YOLO + SIFT)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_event() -> None:
    camera_service.release()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "mode": "YOLO_Alignment"}

# INFERENCE 
@app.post("/api/inference")
async def run_inference(file: UploadFile = File(...)) -> dict:
    result = await inference_service.run(file)
    return result.dict()


@app.get("/api/stream/frame")
async def get_stream_frame() -> Response:
  """Trả về frame từ video stream - ưu tiên camera ngoài, sau đó dataset, cuối cùng placeholder."""
  frame = camera_service.get_frame()
  if frame:
    return Response(content=frame, media_type="image/jpeg")
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
