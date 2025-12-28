from __future__ import annotations
import json
import os
from datetime import datetime
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from fastapi import UploadFile
from ultralytics import YOLO

try:
    import cloudinary
    import cloudinary.uploader
except Exception:
    cloudinary = None

from ..core.config import Settings
from ..models.dto import BoundingBox, InferenceResponse, MissingArea, BoardProfile

logger = logging.getLogger(__name__)

class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        
        # Try multiple model paths (model nằm ngoài backend: ../data/artifacts/)
        model_paths = [
            Path(__file__).parent.parent.parent.parent / "data" / "artifacts" / "best.pt",  # Từ app/services/ lên 4 cấp
            Path("../data/artifacts/best.pt"),  # Từ backend/ lên 1 cấp
            Path("yolov8n.pt")
        ]
        
        model_path = None
        for path in model_paths:
            if path.exists():
                model_path = path
                break
        
        if model_path and model_path.name == "best.pt":
            logger.info(f"✓ Đã load model YOLO từ: {model_path.absolute()}")
            self.model = YOLO(str(model_path))
        else:
            logger.warning("Không tìm thấy best.pt, dùng yolov8n.pt")
            self.model = YOLO("yolov8n.pt")
        
        # Configure Cloudinary uploads
        self._cloudinary_enabled = False
        self._cloudinary_folder = os.getenv("CLOUDINARY_FOLDER", "pcb-inspector")
        cloudinary_url = os.getenv("CLOUDINARY_URL")
        if cloudinary_url and cloudinary is not None:
            try:
                cloudinary.config(cloudinary_url=cloudinary_url)
                self._cloudinary_enabled = True
                logger.info("✓ Upload annotated image lên Cloudinary được bật")
            except Exception as exc:
                logger.warning("Không cấu hình Cloudinary: %s", exc)
        elif cloudinary_url and cloudinary is None:
            logger.warning("Đã đặt CLOUDINARY_URL nhưng chưa cài thư viện cloudinary")
             
        # Cache profile & SIFT data
        self._current_profile: Optional[BoardProfile] = None
        self._ref_image_cache: Optional[np.ndarray] = None
        
        self._sift = cv2.SIFT_create()
        self._ref_kp = None 
        self._ref_des = None
        self._last_aligned_img: Optional[np.ndarray] = None  # Cache ảnh đã align để vẽ 

    def _create_pcb_mask(self, img: np.ndarray) -> np.ndarray:
        """Logic tạo mask giữ nguyên từ collab.py"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

    def _upload_annotated_image(self, image_bytes: bytes | None) -> Optional[str]:
        """Upload ảnh annotated lên Cloudinary và trả về URL."""
        if not image_bytes or not self._cloudinary_enabled:
            return None
        try:
            response = cloudinary.uploader.upload(
                image_bytes,
                folder=self._cloudinary_folder,
                resource_type="image",
                overwrite=True,
            )
            url = response.get("secure_url") or response.get("url")
            logger.info(f"✓ Uploaded to Cloudinary: {url}")
            return url
        except Exception as exc:
            logger.warning(f"Upload annotated image thất bại: {exc}")
            return None

    def estimate_frame_quality(self, img: np.ndarray) -> int:
        """Trả về số keypoints SIFT (dùng để chọn frame camera tốt nhất)."""
        try:
            mask = self._create_pcb_mask(img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            kp, _ = self._sift.detectAndCompute(gray, mask)
            return len(kp) if kp is not None else 0
        except Exception as exc:
            logger.warning(f"Không đo được quality frame: {exc}")
            return 0

    def _load_active_profile(self) -> None:
        """Load profile và cache SIFT keypoints"""
        try:
            active_file = self._settings.artifacts_dir / "active_profile.txt"
            if not active_file.exists():
                # Fallback nếu không có file active, lấy file json đầu tiên
                json_files = list((self._settings.artifacts_dir / "templates").glob("*.json"))
                if not json_files: return
                profile_name = json_files[0].stem
            else:
                profile_name = active_file.read_text(encoding="utf-8").strip()

            json_path = self._settings.artifacts_dir / "templates" / f"{profile_name}.json"
            
            if json_path.exists():
                data = json.loads(json_path.read_text(encoding="utf-8"))
                self._current_profile = BoardProfile(**data)
                
                ref_path = Path(self._current_profile.reference_image_path)
                if not ref_path.exists():
                    # Fallback: nếu đường dẫn trong JSON là absolute (Linux) thì tìm theo tên file trong artifacts/templates
                    candidate = self._settings.artifacts_dir / "templates" / ref_path.name
                    if candidate.exists():
                        ref_path = candidate

                if ref_path.exists():
                    self._ref_image_cache = cv2.imread(str(ref_path))
                    
                    # Pre-calculate SIFT cho ảnh tham chiếu
                    mask_ref = self._create_pcb_mask(self._ref_image_cache)
                    gray_ref = cv2.cvtColor(self._ref_image_cache, cv2.COLOR_BGR2GRAY)
                    self._ref_kp, self._ref_des = self._sift.detectAndCompute(gray_ref, mask_ref)
                    logger.info(f"✓ Loaded profile '{profile_name}' với reference {ref_path}")
                    
        except Exception as e:
            logger.error(f"Error loading profile: {e}")

    async def run(self, upload: UploadFile) -> InferenceResponse:
        contents = await upload.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self._analyze(img)

    async def analyze_bytes(self, data: bytes) -> InferenceResponse:
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self._analyze(img)

    async def analyze_image(self, img: np.ndarray) -> InferenceResponse:
        """API wrapper: Phân tích từ numpy array BGR (cho camera raw frame)."""
        return self._analyze(img)

    async def analyze_and_render(
        self, img: np.ndarray
    ) -> Tuple[InferenceResponse, Optional[bytes], Optional[str]]:
        """Chạy inference + render boxes + trả ảnh trực tiếp (không upload Cloudinary)."""
        result = await self.analyze_image(img)
        annotated = self.draw_detection_boxes(img, result)
        annotated_bytes = annotated if annotated else None
        # Tắt upload Cloudinary để giảm thời gian response
        annotated_url = None
        return result, annotated_bytes, annotated_url

    def _align_image(self, target_img: np.ndarray) -> np.ndarray:
        """
        Logic Align giữ nguyên từ collab.py: 
        Rotation check -> SIFT -> Affine Partial
        """
        if self._ref_image_cache is None or self._ref_des is None: 
            return target_img
            
        h_ref, w_ref = self._ref_image_cache.shape[:2]
        h_tgt, w_tgt = target_img.shape[:2]
        logger.info(f"Alignment: Ref={w_ref}x{h_ref}, Target={w_tgt}x{h_tgt}")
        
        # 1. Rotation logic
        if (w_ref > h_ref) and (h_tgt > w_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)
            logger.info("→ Đã xoay ảnh 90° (portrait→landscape)")
        elif (h_ref > w_ref) and (w_tgt > h_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)
            logger.info("→ Đã xoay ảnh 90° (landscape→portrait)")

        # 2. SIFT Matching
        mask_tgt = self._create_pcb_mask(target_img)
        gray_tgt = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        kp2, des2 = self._sift.detectAndCompute(gray_tgt, mask_tgt)
        
        if des2 is None or len(kp2) < 5:
            logger.warning(f"SIFT không đủ keypoints ({len(kp2) if kp2 else 0}), bỏ qua warp")
            return target_img
        
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(self._ref_des, des2, k=2)
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance: good.append(m)
            
        if len(good) > 10:
            logger.info(f"SIFT: {len(good)} good matches → Affine warp")
            src_pts = np.float32([self._ref_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            
            # 3. Affine Partial (Xoay + Dịch + Scale)
            M, inliers = cv2.estimateAffinePartial2D(dst_pts, src_pts)
            if M is not None:
                logger.info("→ Đã warp ảnh về kích thước ref")
                return cv2.warpAffine(target_img, M, (w_ref, h_ref), flags=cv2.INTER_CUBIC)
        else:
            logger.warning(f"SIFT chỉ có {len(good)} matches (<10), không warp")
                
        return target_img

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Logic tính IoU giữ nguyên từ collab.py"""
        # box: [x_center, y_center, w, h]
        b1_x1, b1_y1 = box1[0] - box1[2]/2, box1[1] - box1[3]/2
        b1_x2, b1_y2 = box1[0] + box1[2]/2, box1[1] + box1[3]/2
        
        b2_x1, b2_y1 = box2[0] - box2[2]/2, box2[1] - box2[3]/2
        b2_x2, b2_y2 = box2[0] + box2[2]/2, box2[1] + box2[3]/2

        x_left = max(b1_x1, b2_x1)
        y_top = max(b1_y1, b2_y1)
        x_right = min(b1_x2, b2_x2)
        y_bottom = min(b1_y2, b2_y2)

        if x_right < x_left or y_bottom < y_top: return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
        b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)
        
        return intersection_area / float(b1_area + b2_area - intersection_area)

    def _verify_visual(self, aligned_img: np.ndarray, box_norm: List[float]) -> float:
        """Logic Template Matching giữ nguyên từ collab.py"""
        h, w = aligned_img.shape[:2]
        cx, cy, bw, bh = box_norm
        x1 = max(0, int((cx - bw/2) * w))
        y1 = max(0, int((cy - bh/2) * h))
        x2 = min(w, int((cx + bw/2) * w))
        y2 = min(h, int((cy + bh/2) * h))
        
        if x2 <= x1 or y2 <= y1: return 0.0
        try:
            roi_test = aligned_img[y1:y2, x1:x2]
            roi_ref = self._ref_image_cache[y1:y2, x1:x2]
            g_test = cv2.cvtColor(roi_test, cv2.COLOR_BGR2GRAY)
            g_ref = cv2.cvtColor(roi_ref, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(g_test, g_ref, cv2.TM_CCOEFF_NORMED)
            return res[0][0]
        except: return 0.0

    def _analyze(self, image: np.ndarray) -> InferenceResponse:
        """Phân tích PCB và phân biệt linh kiện đủ/thiếu dựa trên template."""
        logger.info(f"Input image shape: {image.shape}")
        
        # Xoay ảnh 90° nếu đang nằm ngang (landscape) để chuyển về dọc (portrait)
        h, w = image.shape[:2]
        if w > h:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            logger.info(f"→ Đã xoay ảnh đầu vào 90° từ landscape {w}x{h} sang portrait {image.shape[1]}x{image.shape[0]}")

        if self._current_profile is None:
            self._load_active_profile()

        # Align ảnh về reference để so sánh với template chính xác hơn
        aligned_image = self._align_image(image) if self._current_profile else image

        # Detect bằng YOLO trên ảnh đã align
        results = self.model(aligned_image, verbose=False, conf=0.25)
        detected_count = len(results[0].boxes) if results else 0
        logger.info(f"YOLO detected {detected_count} components")

        self._last_aligned_img = aligned_image

        detected_components: List[MissingArea] = []
        detected_boxes: List[List[float]] = []

        for r in results:
            for box in r.boxes:
                x_center, y_center, width, height = box.xywhn[0].tolist()
                conf = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self.model.names.get(class_id, "components")

                detected_boxes.append([x_center, y_center, width, height])
                detected_components.append(
                    MissingArea(
                        id=f"component_{len(detected_components)}",
                        description=class_name,
                        confidence=conf,
                        bbox=BoundingBox(
                            x=x_center - width / 2,
                            y=y_center - height / 2,
                            width=width,
                            height=height,
                        ),
                    )
                )

        missing_areas: List[MissingArea] = []
        template_components = self._current_profile.components if self._current_profile else []
        iou_threshold = 0.3
        unmatched_indices = set(range(len(detected_boxes)))

        if template_components:
            logger.info(
                "Template có %d components, detected %d",
                len(template_components),
                detected_count,
            )
            for component in template_components:
                template_box = component.box
                if len(template_box) != 4:
                    continue

                best_idx: Optional[int] = None
                best_iou = 0.0

                for idx in list(unmatched_indices):
                    det_box = detected_boxes[idx]
                    iou = self._calculate_iou(template_box, det_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_idx = idx

                if best_idx is not None and best_iou >= iou_threshold:
                    unmatched_indices.discard(best_idx)
                    continue

                cx, cy, w, h = template_box
                tx1, ty1 = cx - w / 2, cy - h / 2
                tx2, ty2 = cx + w / 2, cy + h / 2

                matched_by_center: Optional[int] = None
                for idx in list(unmatched_indices):
                    det_cx, det_cy, _, _ = detected_boxes[idx]
                    if tx1 <= det_cx <= tx2 and ty1 <= det_cy <= ty2:
                        matched_by_center = idx
                        unmatched_indices.discard(idx)
                        break

                if matched_by_center is not None:
                    continue

                missing_areas.append(
                    MissingArea(
                        id=f"missing_{component.id}",
                        description=component.label,
                        confidence=max(0.1, 1.0 - max(best_iou, 0.0)),
                        bbox=BoundingBox(
                            x=tx1,
                            y=ty1,
                            width=w,
                            height=h,
                        ),
                    )
                )
        else:
            # Không có template → fallback như logic cũ
            missing_areas = detected_components.copy()

        is_defective = len(missing_areas) > 0
        avg_confidence = (
            sum(component.confidence for component in detected_components) / len(detected_components)
            if detected_components
            else 0.0
        )
        board_name = self._current_profile.boardName if self._current_profile else "PCB"
        missing_labels = [area.description for area in missing_areas if area.description]

        if template_components:
            note_text = (
                f"Thiếu {len(missing_areas)} / {len(template_components)} linh kiện."
                if is_defective
                else f"PCB OK - Đủ {detected_count} / {len(template_components)} linh kiện."
            )
        else:
            note_text = (
                f"Phát hiện {len(missing_areas)} lỗi/khuyết tật." if is_defective else "PCB đạt chất lượng."
            )

        return InferenceResponse(
            isDefective=is_defective,
            confidence=avg_confidence,
            timestamp=datetime.utcnow(),
            boardName=board_name,
            missingAreas=missing_areas,
            detectedComponents=detected_components,
            missingComponentLabels=missing_labels,
            notes=note_text,
        )

    def draw_detection_boxes(self, img: np.ndarray, result: InferenceResponse) -> bytes:
        """Vẽ bounding boxes lên ảnh và trả về JPEG bytes."""
        # Sử dụng ảnh đã align (sau xoay + warp) thay vì ảnh gốc
        aligned = self._last_aligned_img if self._last_aligned_img is not None else img
        if aligned is None or result is None:
            return b""
        
        vis = aligned.copy()
        h, w = vis.shape[:2]
        
        detected_components = getattr(result, "detectedComponents", [])
        logger.info(
            "Drawing boxes on aligned image: WxH=%dx%d, detected=%d, missing=%d",
            w,
            h,
            len(detected_components),
            len(result.missingAreas),
        )

        # Vẽ linh kiện đủ (màu xanh)
        for component in detected_components:
            if not component.bbox:
                continue
            x1 = int(component.bbox.x * w)
            y1 = int(component.bbox.y * h)
            x2 = int((component.bbox.x + component.bbox.width) * w)
            y2 = int((component.bbox.y + component.bbox.height) * h)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 4)
            label = f"{component.description} {component.confidence:.0%}"
            cv2.putText(vis, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Vẽ linh kiện thiếu (màu đỏ)
        for area in result.missingAreas:
            if not area.bbox:
                continue
            x1 = int(area.bbox.x * w)
            y1 = int(area.bbox.y * h)
            x2 = int((area.bbox.x + area.bbox.width) * w)
            y2 = int((area.bbox.y + area.bbox.height) * h)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 4)
            label = f"MISSING: {area.description}"
            cv2.putText(vis, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Encode JPEG để stream
        success, buffer = cv2.imencode('.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            logger.error("Không encode được ảnh annotated")
            return b""
        
        # Save to temp file for debugging
        temp_path = "/tmp/annotated_result.jpg"
        cv2.imwrite(temp_path, vis)
        logger.info(f"✓ Đã lưu ảnh annotated: {temp_path} (shape={vis.shape})")
        
        return buffer.tobytes()