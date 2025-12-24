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
    # Nếu camera_index là None, sử dụng camera index 0
    if camera_index is None:
      # Sử dụng index 0 - camera mặc định (có thể thay đổi từ FE)
      self._camera_index = 0
      logger.info(f"Sử dụng camera mặc định tại index 0")
    else:
      self._camera_index = camera_index
      logger.info(f"Sử dụng camera index {camera_index} (từ CAMERA_INDEX env var hoặc FE)")
    self._cap: cv2.VideoCapture | None = None
    self._lock = threading.Lock()
    self._last_frame: bytes | None = None
    self._last_frame_time: float = 0.0
    self._frame_cache_duration = 0.03  # Cache 30ms để tránh read quá nhiều
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
        # Thử set resolution cao, nhưng không bắt buộc (DroidCam có thể không hỗ trợ)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Lấy resolution thực tế mà camera đang dùng
        actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera resolution: {actual_width}x{actual_height} @ {actual_fps}fps")
        
        # Cấu hình focus cho khoảng cách ngắn (30cm)
        try:
          import subprocess
          device_path = f"/dev/video{self._camera_index}"
          focus_configured = False
          
          # Tắt autofocus để có thể set manual focus distance
          try:
            result = subprocess.run(
              ["v4l2-ctl", "-d", device_path, "-c", "focus_auto=0"],
              capture_output=True,
              text=True,
              timeout=2
            )
            if result.returncode == 0:
              logger.info("Đã tắt autofocus, sẵn sàng set manual focus")
              
              # Set focus distance cho khoảng cách ngắn (30cm)
              # Giá trị focus thường từ 0-255, với giá trị thấp = gần, cao = xa
              # Thử các giá trị: 0, 10, 20, 30 cho khoảng cách 30cm
              focus_values = [0, 10, 20, 30, 40, 50]
              
              for focus_val in focus_values:
                result = subprocess.run(
                  ["v4l2-ctl", "-d", device_path, "-c", f"focus_absolute={focus_val}"],
                  capture_output=True,
                  text=True,
                  timeout=2
                )
                if result.returncode == 0:
                  logger.info(f"✓ Đã set focus_absolute={focus_val} (khoảng cách ngắn ~30cm)")
                  focus_configured = True
                  break
              
              # Nếu không set được focus_absolute, thử lại với autofocus ở chế độ macro
              if not focus_configured:
                # Thử bật lại autofocus với range gần
                subprocess.run(
                  ["v4l2-ctl", "-d", device_path, "-c", "focus_auto=1"],
                  capture_output=True,
                  timeout=2
                )
                logger.info("Đã bật lại autofocus (fallback)")
                focus_configured = True
          
          except FileNotFoundError:
            logger.warning("v4l2-ctl không có sẵn, không thể điều chỉnh focus distance")
          except Exception as e:
            logger.warning(f"Lỗi khi set manual focus: {e}")
          
          # Fallback: Thử với OpenCV API
          if not focus_configured:
            try:
              # Tắt autofocus
              self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
              # Set focus cho khoảng cách ngắn (0-255, giá trị thấp = gần)
              focus_set = self._cap.set(cv2.CAP_PROP_FOCUS, 30)
              if focus_set:
                logger.info("Đã set focus distance qua OpenCV (giá trị 30 cho ~30cm)")
                focus_configured = True
              else:
                # Nếu không được, bật lại autofocus
                self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                logger.info("Manual focus không hỗ trợ, bật lại autofocus")
            except Exception as e:
              logger.warning(f"Lỗi khi set focus qua OpenCV: {e}")
          
          if not focus_configured:
            logger.warning("Không thể cấu hình focus distance, camera sẽ dùng chế độ mặc định")
        
        except Exception as e:
          logger.warning(f"Lỗi tổng quát khi cấu hình focus: {e}")
        
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

  def get_raw_frame(self) -> np.ndarray | None:
    """Lấy frame RAW từ camera (BGR format) - dùng cho detection chất lượng cao."""
    with self._lock:
      if not self._initialize_camera():
        return None

      if self._cap is None:
        return None

      try:
        ret, frame = self._cap.read()
        if not ret or frame is None:
          return None
        return frame  # Trả về raw numpy array BGR
      except Exception as e:
        logger.error(f"Lỗi đọc raw frame: {e}")
        return None

  def get_frame(self) -> bytes | None:
    """Lấy frame từ camera dưới dạng JPEG bytes (nén cho streaming)."""
    import time
    
    with self._lock:
      # Cache frame trong 30ms để tránh read quá nhiều lần
      current_time = time.time()
      if self._last_frame and (current_time - self._last_frame_time) < self._frame_cache_duration:
        return self._last_frame
      
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
        
        # Resize nhỏ hơn để stream nhanh (640x480 thay vì 1280x720)
        img.thumbnail((640, 480), Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes với quality thấp hơn để giảm size
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        buffer.seek(0)
        
        frame_bytes = buffer.read()
        self._last_frame = frame_bytes
        self._last_frame_time = current_time
        return frame_bytes
      except Exception:
        return self._last_frame

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

  def is_opened(self) -> bool:
    """Kiểm tra camera có đang mở không."""
    with self._lock:
      return self._cap is not None and self._cap.isOpened()

  def switch_camera(self, new_index: int) -> bool:
    """Chuyển sang camera index khác."""
    with self._lock:
      # Đóng camera hiện tại
      if self._cap is not None:
        self._cap.release()
        self._cap = None
      
      # Mở camera mới
      self._camera_index = new_index  # Sửa thành _camera_index
      self._cap = cv2.VideoCapture(new_index)
      
      if not self._cap.isOpened():
        logger.error(f"Không thể mở camera index {new_index}")
        self._cap = None
        return False
      
      # Cấu hình lại
      self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
      self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
      self._cap.set(cv2.CAP_PROP_FPS, 30)
      self._is_initialized = True
      logger.info(f"Đã chuyển sang camera index {new_index}")
      return True

  def __del__(self) -> None:
    """Destructor để đảm bảo camera được giải phóng."""
    self.release()

