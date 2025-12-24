from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any

import cv2
import numpy as np
import serial
from serial import SerialException

from ..models.dto import InferenceResponse
from .camera_service import CameraService
from .inference import InferenceService

logger = logging.getLogger(__name__)


class LineController:
    """Quản lý kết nối Serial tới Arduino Nano và tự động chạy inference."""

    def __init__(
        self,
        camera_service: CameraService,
        inference_service: InferenceService,
        port: str | None = None,
        baud: int | None = None,
    ) -> None:
        self.camera_service = camera_service
        self.inference_service = inference_service
        self.port = port or os.getenv("NANO_PORT", "COM33")
        self.baud = baud or int(os.getenv("NANO_BAUD", "115200"))
        self._serial: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._waiting = False
        self._status_snapshot: dict[str, Any] = {"RUN": False, "WAIT": False, "REJECTPEND": False}
        self.ok_count = 0
        self.ng_count = 0
        self.last_status_raw: str | None = None
        self.last_result: InferenceResponse | None = None
        self.last_annotated_frame: bytes | None = None
        self.last_annotated_url: str | None = None
        self.annotated_frame_timestamp: float = 0.0  # Timestamp khi có detection
        self.frame_sample_count = 3

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._running:
            return
        
        # LUÔN set loop ngay cả khi không có Arduino (để test detection hoạt động)
        self._loop = loop
        
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.1)
        except SerialException as exc:
            logger.warning("Không thể mở cổng %s (%s) - Test detection vẫn hoạt động", self.port, exc)
            return
        
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        logger.info("Đã kết nối Arduino Nano tại %s @ %d bps", self.port, self.baud)

    def stop(self) -> None:
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=1)
            self._reader_thread = None
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except SerialException:
                pass
        self._serial = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "baud": self.baud,
            "connected": bool(self._serial and self._serial.is_open),
            "okCount": self.ok_count,
            "ngCount": self.ng_count,
            "machineState": self._status_snapshot,
            "waitingForDetection": self._waiting,
            "lastInference": self.last_result.dict() if self.last_result else None,
            "lastStatusRaw": self.last_status_raw,
        }

    def get_last_inference(self) -> InferenceResponse | None:
        """Trả về kết quả inference mới nhất (để FE hiển thị missing components)."""
        return self.last_result

    def get_annotated_frame(self) -> bytes | None:
        """Trả về frame đã vẽ bounding boxes mới nhất (nếu có)."""
        with self._lock:
            return self.last_annotated_frame

    def get_last_snapshot(self) -> dict[str, Any] | None:
        """Lấy snapshot detection mới nhất gồm ảnh + kết quả."""
        with self._lock:
            if not self.last_result and not self.last_annotated_frame:
                return None
            return {
                "result": self.last_result,
                "frame": self.last_annotated_frame,
                "frameUrl": self.last_annotated_url,
                "timestamp": self.annotated_frame_timestamp,
            }

    def update_last_detection(
        self,
        result: InferenceResponse,
        annotated_frame: bytes | None,
        annotated_url: str | None,
    ) -> None:
        """Cập nhật cache kết quả detection gần nhất để FE đọc lại."""
        with self._lock:
            self.last_result = result
            self.last_annotated_frame = annotated_frame
            self.last_annotated_url = annotated_url
            self.annotated_frame_timestamp = time.time()

    def trigger_manual_detection(self) -> bool:
        """Trigger detection thủ công từ UI (giả lập EVENT:BOARD_AT_CAMERA)."""
        if self._waiting:
            logger.warning("Detection đang chạy, bỏ qua trigger thủ công")
            return False
        if not self._loop:
            logger.warning("Event loop chưa sẵn sàng")
            return False
        self._schedule_detection()
        logger.info("Manual detection triggered từ UI")
        return True

    def send_command(self, command: str) -> bool:
        payload = command.strip()
        if not payload:
            return False
        with self._lock:
            if not self._serial or not self._serial.is_open:
                logger.warning("Serial chưa sẵn sàng, bỏ qua command %s", payload)
                return False
            try:
                self._serial.write((payload + "\n").encode("utf-8"))
                logger.debug("Nano <= %s", payload)
                return True
            except SerialException as exc:
                logger.error("Gửi command thất bại: %s", exc)
                return False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _reader_loop(self) -> None:
        while self._running and self._serial:
            try:
                line = self._serial.readline()
            except SerialException as exc:
                logger.error("Serial lỗi khi đọc: %s", exc)
                break
            if not line:
                continue
            try:
                text = line.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if not text:
                continue
            # Log tất cả messages từ Arduino
            if text.startswith("EVENT:"):
                logger.info("📡 Arduino => %s", text)
            else:
                logger.debug("Nano => %s", text)
            self._handle_line(text)
        logger.info("Reader thread stopped")

    def _handle_line(self, line: str) -> None:
        if line.startswith("STATUS:"):
            self.last_status_raw = line
            self._parse_status(line)
            return
        if line == "EVENT:BOARD_AT_CAMERA":
            logger.info("🎯 Nhận EVENT: Băng tải dừng, bắt đầu detection!")
            self._schedule_detection()
            return
        if line == "EVENT:RESET_DONE":
            self.ok_count = 0
            self.ng_count = 0
            self._status_snapshot.update({"WAIT": False, "REJECTPEND": False})
            return
        if line.startswith("ERROR:"):
            logger.warning("Nano báo lỗi: %s", line)
            return
        # Các event khác chỉ log lại
        if line.startswith("EVENT:"):
            logger.info(line)

    def _parse_status(self, line: str) -> None:
        payload = line.removeprefix("STATUS:")
        tokens = payload.split(",")
        snapshot = dict(self._status_snapshot)
        for token in tokens:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            key = key.strip().upper()
            value = value.strip()
            if key == "OK":
                try:
                    self.ok_count = int(value)
                except ValueError:
                    pass
            elif key == "NG":
                try:
                    self.ng_count = int(value)
                except ValueError:
                    pass
            elif key in ("RUN", "WAIT", "REJECTPEND"):
                snapshot[key] = value == "1"
        self._status_snapshot = snapshot

    def _schedule_detection(self) -> None:
        if not self._loop:
            logger.warning("❌ Event loop chưa sẵn sàng, bỏ qua detection")
            return
        if self._waiting:
            logger.warning("⏳ Detection đang chạy, bỏ qua trigger mới")
            return
        self._waiting = True
        self._status_snapshot["WAIT"] = True
        logger.info("✅ Scheduled detection task")
        future = asyncio.run_coroutine_threadsafe(self._auto_detect(), self._loop)
        future.add_done_callback(lambda _: None)

    async def _auto_detect(self) -> None:
        try:
            # Đợi 1 giây để băng tải dừng hẳn và ổn định
            await asyncio.sleep(1.0)
            logger.info("⏱️  Đợi băng tải dừng ổn định (1s)")
            
            # Chụp 1 frame duy nhất
            img = await asyncio.to_thread(self.camera_service.get_raw_frame)
            if img is None:
                logger.warning("Không có frame camera để detect")
                self.send_command("CMD:RESULT:NG")
                return

            h, w = img.shape[:2]
            logger.info("📸 Camera frame gốc: %dx%d", w, h)
            
            # Crop phần bên trái để loại bỏ sensor/phụ kiện (giữ lại 80% bên phải)
            crop_left = int(w * 0.2)  # Bỏ 20% bên trái
            img_cropped = img[:, crop_left:]  # [y, x] - giữ toàn bộ height, crop width
            h_crop, w_crop = img_cropped.shape[:2]
            logger.info("✂️  Cropped: %dx%d (bỏ %dpx bên trái)", w_crop, h_crop, crop_left)
            
            # Lưu frame gốc để debug
            try:
                cv2.imwrite("/tmp/pcb_capture_raw.jpg", img_cropped)
                logger.info("Đã lưu ảnh đã crop: /tmp/pcb_capture_raw.jpg")
            except Exception as e:
                logger.warning(f"Không lưu được ảnh gốc: {e}")
            
            # Phân tích ảnh đã crop
            result, annotated_frame, annotated_url = await self.inference_service.analyze_and_render(img_cropped)
            self.update_last_detection(result, annotated_frame, annotated_url)
            # Lưu ảnh annotated để xem lại
            try:
                if annotated_frame:
                    cv_img = cv2.imdecode(np.frombuffer(annotated_frame, np.uint8), cv2.IMREAD_COLOR)
                    if cv_img is not None:
                        cv2.imwrite("/tmp/pcb_capture_annotated.jpg", cv_img)
                        logger.info("Đã lưu ảnh annotated: /tmp/pcb_capture_annotated.jpg")
            except Exception as e:
                logger.warning(f"Không lưu được ảnh annotated: {e}")
            
            command = "CMD:RESULT:NG" if result.isDefective else "CMD:RESULT:OK"
            self.send_command(command)
            logger.info("Auto detect => defect=%s, gửi %s", result.isDefective, command)
        except Exception as exc:
            logger.exception("Lỗi auto detect: %s", exc)
            self.send_command("CMD:RESULT:NG")
        finally:
            self._waiting = False
            self._status_snapshot["WAIT"] = False
