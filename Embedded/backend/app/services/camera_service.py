from __future__ import annotations

import io
import logging
import threading
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..core.config import Settings

logger = logging.getLogger(__name__)


class CameraService:
  """Service để quản lý camera và stream frame."""

  @staticmethod
  def _is_infrared_device(index: int) -> bool:
    """Kiểm tra xem video device có phải camera hồng ngoại hay không."""
    sysfs_path = Path(f"/sys/class/video4linux/video{index}/name")
    try:
      name = sysfs_path.read_text(encoding="utf-8").strip().lower()
    except Exception:
      return False
    keywords = ["infrared", "ir camera", "depth", "noir"]
    return any(keyword in name for keyword in keywords)

  @classmethod
  def detect_external_camera(cls, max_index: int = 10) -> int | None:
    """Tự động phát hiện camera ngoài (bỏ qua laptop + camera IR)."""
    # Thử các index từ 1 trở đi (bỏ qua 0 - camera laptop)
    for index in range(1, max_index + 1):
      if cls._is_infrared_device(index):
        logger.info(f"Skip camera index {index} do nhận dạng là camera hồng ngoại")
        continue
      try:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
          # Thử đọc một frame để đảm bảo camera thực sự hoạt động
          ret, _ = cap.read()
          cap.release()
          if ret:
            return index
        cap.release()
      except Exception:
        continue
    return None

  def __init__(self, settings: Settings, camera_index: int | None = None) -> None:
    self._settings = settings
    # Nếu camera_index là None, tự động detect camera ngoài
    if camera_index is None:
      logger.info("Đang tự động phát hiện camera ngoài...")
      detected = self.detect_external_camera()
      if detected is not None:
        self._camera_index = detected
        logger.info(f"Đã phát hiện camera ngoài tại index {detected}")
      else:
        # Fallback về index 1 nếu không detect được
        self._camera_index = 1
        logger.warning("Không phát hiện được camera ngoài, sử dụng index 1 (có thể không hoạt động)")
    else:
      self._camera_index = camera_index
      logger.info(f"Sử dụng camera index {camera_index} (từ CAMERA_INDEX env var)")
    self._cap: cv2.VideoCapture | None = None
    self._lock = threading.Lock()
    self._last_frame: bytes | None = None
    self._is_initialized = False

  def _initialize_camera(self) -> bool:
    """Khởi tạo camera nếu chưa có."""
    if self._is_initialized and self._cap is not None:
      if self._cap.isOpened():
        return True
      else:
        # Camera đã bị đóng, reset và thử lại
        logger.warning("Camera đã bị đóng, đang thử khởi tạo lại...")
        self._is_initialized = False
        if self._cap is not None:
          self._cap.release()
          self._cap = None

    try:
      logger.info(f"Đang mở camera tại index {self._camera_index}...")
      self._cap = cv2.VideoCapture(self._camera_index)
      if self._cap.isOpened():
        # Set resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Bật autofocus (tự động lấy nét)
        try:
          # Thử nhiều cách để bật autofocus
          autofocus_success = False
          
          # Cách 1: CAP_PROP_AUTOFOCUS = 39
          if self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 1):
            autofocus_success = True
            logger.info("Đã bật autofocus qua CAP_PROP_AUTOFOCUS")
          
          # Cách 2: CAP_PROP_FOCUS = 28, set = 0 để auto
          if self._cap.set(cv2.CAP_PROP_FOCUS, 0):
            autofocus_success = True
            logger.info("Đã set focus mode = auto qua CAP_PROP_FOCUS")
          
          # Cách 3: Dùng v4l2-ctl nếu có (cho USB camera như Brio 100)
          if not autofocus_success:
            try:
              import subprocess
              # Tìm device path từ camera index
              device_path = f"/dev/video{self._camera_index}"
              # Bật autofocus qua v4l2-ctl
              result = subprocess.run(
                ["v4l2-ctl", "-d", device_path, "-c", "focus_auto=1"],
                capture_output=True,
                text=True,
                timeout=2
              )
              if result.returncode == 0:
                logger.info("Đã bật autofocus qua v4l2-ctl")
                autofocus_success = True
            except FileNotFoundError:
              logger.debug("v4l2-ctl không có sẵn, bỏ qua")
            except Exception as e:
              logger.debug(f"Không thể dùng v4l2-ctl: {e}")
          
          if not autofocus_success:
            logger.warning("Không thể bật autofocus (có thể camera không hỗ trợ hoặc cần cấu hình thủ công)")
        except Exception as e:
          logger.warning(f"Lỗi khi cấu hình autofocus: {e}")
        
        # Thử đọc một frame để đảm bảo camera hoạt động
        ret, _ = self._cap.read()
        if ret:
          self._is_initialized = True
          logger.info(f"Camera đã được khởi tạo thành công tại index {self._camera_index}")
          return True
        else:
          logger.warning(f"Camera index {self._camera_index} mở được nhưng không đọc được frame")
          self._cap.release()
          self._cap = None
          return False
      else:
        logger.error(f"Không thể mở camera tại index {self._camera_index}")
        return False
    except Exception as e:
      logger.error(f"Lỗi khi khởi tạo camera tại index {self._camera_index}: {e}")
      return False

  @property
  def camera_index(self) -> int:
    """Lấy camera index hiện tại."""
    return self._camera_index

  def initialize(self) -> bool:
    """Public method để khởi tạo camera (có thể gọi từ bên ngoài)."""
    with self._lock:
      return self._initialize_camera()

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

