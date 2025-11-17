from __future__ import annotations

import io
import threading
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..core.config import Settings


class CameraService:
  """Service để quản lý camera và stream frame."""

  def __init__(self, settings: Settings, camera_index: int = 0) -> None:
    self._settings = settings
    self._camera_index = camera_index
    self._cap: cv2.VideoCapture | None = None
    self._lock = threading.Lock()
    self._last_frame: bytes | None = None
    self._is_initialized = False

  def _initialize_camera(self) -> bool:
    """Khởi tạo camera nếu chưa có."""
    if self._is_initialized and self._cap is not None:
      return self._cap.isOpened()

    try:
      self._cap = cv2.VideoCapture(self._camera_index)
      if self._cap.isOpened():
        # Set resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._is_initialized = True
        return True
      return False
    except Exception:
      return False

  def get_frame(self) -> bytes | None:
    """Lấy frame từ camera dưới dạng JPEG bytes."""
    with self._lock:
      if not self._initialize_camera():
        return None

      if self._cap is None:
        return None

      try:
        ret, frame = self._cap.read()
        if not ret or frame is None:
          return self._last_frame  # Trả về frame cũ nếu không đọc được

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        img = Image.fromarray(frame_rgb)
        
        # Resize nếu cần
        img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        
        frame_bytes = buffer.read()
        self._last_frame = frame_bytes
        return frame_bytes
      except Exception:
        return self._last_frame

  def get_frame_from_dataset(self, dataset_service=None) -> bytes | None:
    """Lấy frame từ dataset nếu không có camera."""
    if dataset_service is None:
      from .dataset_service import DatasetService
      dataset_service = DatasetService(self._settings)
    samples = dataset_service.list_samples()
    
    if not samples:
      return None
    
    try:
      latest = sorted(samples, key=lambda x: x.createdAt, reverse=True)[0]
      image_path = Path(latest.path)
      if image_path.exists():
        img = Image.open(image_path)
        if img.mode != "RGB":
          img = img.convert("RGB")
        img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return buffer.read()
    except Exception:
      pass
    
    return None

  def get_placeholder_frame(self) -> bytes:
    """Tạo placeholder frame."""
    img = Image.new("RGB", (640, 360), color=(40, 40, 40))
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    
    try:
      font = ImageFont.load_default()
    except Exception:
      font = None
    
    text = "Camera không khả dụng\n(Demo Mode)"
    bbox = draw.textbbox((0, 0), text, font=font) if font else (0, 0, 200, 40)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((640 - text_width) // 2, (360 - text_height) // 2)
    draw.text(position, text, fill=(200, 200, 200), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer.read()

  def release(self) -> None:
    """Giải phóng camera."""
    with self._lock:
      if self._cap is not None:
        self._cap.release()
        self._cap = None
      self._is_initialized = False

  def __del__(self) -> None:
    """Destructor để đảm bảo camera được giải phóng."""
    self.release()

