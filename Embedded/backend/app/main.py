from __future__ import annotations

import asyncio
import os
import json
import logging
import base64

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from .core.config import get_settings
from .services.camera_service import CameraService
from .services.inference_service import InferenceService
from .services.line_controller import LineController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
inference_service = InferenceService(settings)

camera_index_env = os.getenv("CAMERA_INDEX")
camera_index = int(camera_index_env) if camera_index_env is not None else 0
camera_service = CameraService(settings, camera_index=camera_index)

if camera_service.initialize():
    logger.info(f"Camera đã sẵn sàng tại index {camera_service.camera_index}")
else:
    logger.warning(f"Không mở được camera index {camera_service.camera_index}")

line_controller = LineController(camera_service, inference_service)

app = FastAPI(title="PCB Inspector API (YOLO + SIFT)", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event() -> None:
  loop = asyncio.get_running_loop()
  line_controller.start(loop)


@app.on_event("shutdown")
async def shutdown_event() -> None:
  line_controller.stop()
  camera_service.release()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "mode": "YOLO_Alignment"}

# INFERENCE 
@app.post("/api/inference")
async def run_inference(file: UploadFile = File(...)) -> dict:
    # Đọc file upload một lần duy nhất
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Phân tích từ numpy array (không dùng file.read() nữa)
    result = await inference_service.analyze_image(img)
    
    # Vẽ bounding boxes lên ảnh
    annotated_bytes = inference_service.draw_detection_boxes(img, result)
    annotated_base64 = base64.b64encode(annotated_bytes).decode('utf-8') if annotated_bytes else None
    
    # Trả về JSON + ảnh đã vẽ boxes (base64)
    response = result.dict()
    response['annotatedImage'] = annotated_base64
    return response


@app.get("/api/stream/frame")
async def get_stream_frame() -> Response:
  """Trả về frame từ camera (raw, không có boxes) - stream liên tục."""
  # LUÔN trả raw camera frame để stream mượt
  frame = camera_service.get_frame()
  if frame:
    return Response(content=frame, media_type="image/jpeg")
  
  # Placeholder nếu không có camera
  frame = camera_service.get_placeholder_frame()
  return Response(content=frame, media_type="image/jpeg")


@app.get("/api/stream/annotated")
async def get_annotated_frame() -> Response:
  """Lấy frame có bounding boxes (detection result)."""
  annotated = line_controller.get_annotated_frame()
  if annotated:
    return Response(content=annotated, media_type="image/jpeg")
  
  # Fallback về raw frame nếu chưa có detection
  frame = camera_service.get_frame()
  if frame:
    return Response(content=frame, media_type="image/jpeg")
  
  # Placeholder cuối cùng
  frame = camera_service.get_placeholder_frame()
  return Response(content=frame, media_type="image/jpeg")


@app.get("/api/stream/mjpeg")
async def get_mjpeg_stream(request: Request) -> StreamingResponse:
  """MJPEG stream endpoint - stream video mượt hơn, ưu tiên annotated frame."""
  async def generate_frames():
    try:
      while True:
        # Kiểm tra nếu client đã disconnect
        if await request.is_disconnected():
          break
        
        # Ưu tiên frame đã vẽ boxes từ line controller
        frame = line_controller.get_annotated_frame()
        
        if not frame:
          # Fallback camera frame thường
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


class LineCommand(BaseModel):
  command: str


@app.get("/api/line/status")
async def get_line_status() -> dict:
  """Lấy trạng thái băng tải (OK/NG count, machine state, last inference)."""
  return line_controller.get_status()


@app.get("/api/line/last_inference")
async def get_line_last_inference() -> dict:
  """Lấy kết quả inference mới nhất từ auto-detection (giống format API /api/inference)."""
  result = line_controller.get_last_inference()
  if not result:
    raise HTTPException(status_code=404, detail="Chưa có inference nào từ băng tải")
  return result.dict()


@app.post("/api/line/command")
async def send_line_command(payload: LineCommand) -> dict:
  success = line_controller.send_command(payload.command)
  if not success:
    raise HTTPException(status_code=400, detail="Không gửi được command (Serial chưa kết nối)")
  return {"sent": payload.command}


@app.post("/api/line/test_detection")
async def test_detection() -> dict:
  """Trigger detection thủ công (giả lập EVENT:BOARD_AT_CAMERA từ Arduino)."""
  success = line_controller.trigger_manual_detection()
  if not success:
    raise HTTPException(status_code=400, detail="Không thể trigger detection (đang xử lý hoặc chưa sẵn sàng)")
  return {"status": "detection_triggered"}


@app.get("/api/config/available_ports")
async def get_available_ports() -> dict:
  """Liệt kê các serial ports khả dụng trên hệ thống."""
  import glob
  ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
  ports.sort()
  return {"ports": ports, "current": line_controller.port}


class CameraConfig(BaseModel):
  camera_index: int


@app.post("/api/config/camera")
async def set_camera_index(payload: CameraConfig) -> dict:
  """Thay đổi camera index đang sử dụng."""
  success = camera_service.switch_camera(payload.camera_index)
  if not success:
    raise HTTPException(status_code=400, detail=f"Không thể mở camera index {payload.camera_index}")
  return {"camera_index": payload.camera_index, "status": "switched"}


@app.get("/api/config/camera")
async def get_camera_info() -> dict:
  """Lấy thông tin camera hiện tại."""
  return {"camera_index": camera_service.camera_index, "is_opened": camera_service.is_opened()}
