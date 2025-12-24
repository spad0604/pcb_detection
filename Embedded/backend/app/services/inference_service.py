from __future__ import annotations
import json
import os
from datetime import datetime
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import cv2
import numpy as np
from fastapi import UploadFile
from ultralytics import YOLO

try:
    import cloudinary
    import cloudinary.uploader
except Exception:  # pragma: no cover - optional dependency fallback
    cloudinary = None

from ..core.config import Settings
from ..models.dto import BoundingBox, InferenceResponse, MissingArea, BoardProfile

logger = logging.getLogger(__name__)

class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        
        # Load Model YOLO từ Embedded/data/artifacts/best.pt
        embedded_artifacts = Path(__file__).resolve().parents[3] / "data" / "artifacts" / "best.pt"
        backend_artifacts = Path(__file__).resolve().parents[2] / "data" / "artifacts" / "best.pt"
        candidates = [embedded_artifacts, backend_artifacts, settings.artifacts_dir / "best.pt"]

        self.model_path = next((p for p in candidates if p.exists()), None)
        if self.model_path is None:
            logger.warning("Không tìm thấy best.pt, dùng yolov8n.pt")
            self.model = YOLO("yolov8n.pt")
        else:
            logger.info(f"✓ Đã load model YOLO từ: {self.model_path}")
            self.model = YOLO(str(self.model_path))
        
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
        self._ref_kp = None  # Keypoints của ảnh gốc
        self._ref_des = None # Descriptors của ảnh gốc
        self._last_aligned_img: Optional[np.ndarray] = None  # Cache ảnh đã align để vẽ

    def _create_pcb_mask(self, img: np.ndarray) -> np.ndarray:
        """Tạo mask lọc nền (Chỉ giữ lại mạch xanh dương)."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

    def _upload_annotated_image(self, image_bytes: bytes | None) -> Optional[str]:
        if not image_bytes or not self._cloudinary_enabled:
            return None
        try:
            response = cloudinary.uploader.upload(
                image_bytes,
                folder=self._cloudinary_folder,
                resource_type="image",
                overwrite=True,
            )
            return response.get("secure_url") or response.get("url")
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
        """Load profile và tính toán trước SIFT keypoints cho ảnh chuẩn."""
        try:
            active_file = self._settings.artifacts_dir / "active_profile.txt"
            if not active_file.exists():
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
                if ref_path.exists():
                    self._ref_image_cache = cv2.imread(str(ref_path))
                    
                    mask_ref = self._create_pcb_mask(self._ref_image_cache)
                    gray_ref = cv2.cvtColor(self._ref_image_cache, cv2.COLOR_BGR2GRAY)
                    self._ref_kp, self._ref_des = self._sift.detectAndCompute(gray_ref, mask_ref)
                    
        except Exception as e:
            print(f"Lỗi load profile: {e}")

    async def run(self, upload: UploadFile) -> InferenceResponse:
        contents = await upload.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self._analyze(img)

    async def analyze_bytes(self, data: bytes) -> InferenceResponse:
        
        from ..utils.image_processing import preprocess_image_from_bytes
        img = preprocess_image_from_bytes(data)
        return self._analyze(img)

    async def analyze_image(self, img: np.ndarray) -> InferenceResponse:
        """API wrapper: Phân tích từ numpy array BGR (cho camera raw frame)."""
        return self._analyze(img)

    async def analyze_and_render(
        self, img: np.ndarray
    ) -> Tuple[InferenceResponse, Optional[bytes], Optional[str]]:
        """Chạy inference + render boxes + upload annotated image."""
        result = await self.analyze_image(img)
        annotated = self.draw_detection_boxes(img, result)
        annotated_bytes = annotated if annotated else None
        annotated_url = self._upload_annotated_image(annotated_bytes)
        return result, annotated_bytes, annotated_url

    def draw_detection_boxes(self, img: np.ndarray, result: InferenceResponse) -> bytes:
        """API wrapper: Vẽ bounding boxes lên ảnh và trả về JPEG bytes."""
        # Sử dụng ảnh đã align (sau xoay + warp) thay vì ảnh gốc
        aligned = self._last_aligned_img if self._last_aligned_img is not None else img
        if aligned is None or result is None:
            return b""
        
        vis = aligned.copy()
        h, w = vis.shape[:2]
        
        logger.info(f"Drawing boxes on aligned image: WxH={w}x{h} (shape={vis.shape}), missing areas: {len(result.missingAreas)}")
        
        # Vẽ các vùng thiếu từ result (chỉ box mỏng màu đỏ, không có text)
        for area in result.missingAreas:
            if not area.bbox:
                continue
            x1 = int(area.bbox.x * w)
            y1 = int(area.bbox.y * h)
            x2 = int((area.bbox.x + area.bbox.width) * w)
            y2 = int((area.bbox.y + area.bbox.height) * h)
            logger.info(f"Box: ({x1},{y1}) -> ({x2},{y2}), normalized: ({area.bbox.x:.3f},{area.bbox.y:.3f},{area.bbox.width:.3f},{area.bbox.height:.3f})")
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 5)
        
        # Encode JPEG để stream
        success, buffer = cv2.imencode('.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            return b""
        
        # Debug: Lưu ảnh ra file để kiểm tra
        try:
            cv2.imwrite("/tmp/annotated_result.jpg", vis)
            logger.info(f"✓ Đã lưu ảnh annotated: /tmp/annotated_result.jpg (shape={vis.shape})")
        except Exception as e:
            logger.warning(f"Không lưu được ảnh annotated: {e}")
        
        return buffer.tobytes()

    def _align_image(self, target_img: np.ndarray) -> np.ndarray:
        """Căn chỉnh ảnh dùng Affine Partial + Masking."""
        if self._ref_image_cache is None or self._ref_des is None: 
            logger.warning("Không có ref_image hoặc SIFT descriptors, bỏ qua alignment")
            return target_img
            
        h_ref, w_ref = self._ref_image_cache.shape[:2]
        h_tgt, w_tgt = target_img.shape[:2]
        logger.info(f"Alignment: Ref={w_ref}x{h_ref}, Target={w_tgt}x{h_tgt}")
        
        # 1. Xoay thô nếu ngược chiều
        rotated = False
        if (w_ref > h_ref) and (h_tgt > w_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)
            rotated = True
            logger.info("→ Đã xoay ảnh 90° (portrait→landscape)")
        elif (h_ref > w_ref) and (w_tgt > h_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)
            rotated = True
            logger.info("→ Đã xoay ảnh 90° (landscape→portrait)")

        # 2. SIFT Matching với Mask
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
            
            # 3. Affine Partial:  Rotation + Translation + Scale 
            M, inliers = cv2.estimateAffinePartial2D(dst_pts, src_pts)
            if M is not None:
                logger.info("→ Đã warp ảnh về kích thước ref")
                return cv2.warpAffine(target_img, M, (w_ref, h_ref), flags=cv2.INTER_CUBIC)
        else:
            logger.warning(f"SIFT chỉ có {len(good)} matches (<10), không warp")
                
        return target_img

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Tính IoU giữa 2 box (xywh normalized)."""
        # box: [x_center, y_center, w, h] -> convert to x1, y1, x2, y2
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
        """So khớp hình ảnh (Template Matching) tại vị trí box."""
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
        if self._current_profile is None:
            self._load_active_profile()
            
        if self._current_profile is None or self._ref_image_cache is None:
             return InferenceResponse(
                 isDefective=False, confidence=0.0, timestamp=datetime.utcnow(), 
                 boardName="Chưa Train Mạch", notes="Vui lòng train mạch trước."
             )

        # 1. Alignment (Xoay + SIFT warp)
        logger.info(f"Input image shape: {image.shape}")
        aligned_img = self._align_image(image)
        self._last_aligned_img = aligned_img  # Lưu để vẽ boxes sau
        logger.info(f"Aligned image shape: {aligned_img.shape}")

        # 2. Detect: Lấy tất cả box 
        results = self.model(aligned_img, verbose=False, conf=0.25)
        logger.info(f"YOLO detected {len(results[0].boxes) if results else 0} boxes")
        
        detected_candidates = []
        for r in results:
            for i, box in enumerate(r.boxes):
                detected_candidates.append({
                    'id': i,
                    'box': box.xywhn[0].tolist(), # [x, y, w, h] normalized
                    'conf': float(box.conf[0]),
                    'is_used': False
                })

        # 3. GLOBAL MATCHING LOGIC 
        potential_matches = []
        for temp_comp in self._current_profile.components:
            tx, ty, tw, th = temp_comp.box
            
            for candidate in detected_candidates:
                iou = self._calculate_iou(temp_comp.box, candidate['box'])
                dx, dy, _, _ = candidate['box']
                dist = np.sqrt((tx - dx)**2 + (ty - dy)**2)

                if iou > 0.01 or dist < 0.06:
                    score = iou + (1.0 - dist) 
                    potential_matches.append({
                        'comp_id': temp_comp.id,
                        'comp_box': temp_comp.box,
                        'cand_idx': candidate['id'],
                        'cand_item': candidate,
                        'score': score
                    })

        potential_matches.sort(key=lambda x: x['score'], reverse=True)
        
        matched_results = {} 
        comp_used = set()
        
        for match in potential_matches:
            c_id = match['comp_id']
            cand_item = match['cand_item']
            
            if c_id in comp_used or cand_item['is_used']:
                continue
            
            matched_results[c_id] = match
            cand_item['is_used'] = True
            comp_used.add(c_id)

        missing_areas = []
        
        for temp_comp in self._current_profile.components:
            if temp_comp.id in matched_results:
                # Component đã được detect và match với template
                match = matched_results[temp_comp.id]
                candidate = match['cand_item']
                
                vis_score = self._verify_visual(aligned_img, candidate['box'])
                conf = candidate['conf']

                is_present = (vis_score > 0.15) or (conf > 0.30)
                
                # Nếu detect được thì KHÔNG thêm vào missing (dù confidence thấp)
                # Chỉ log cảnh báo nếu confidence yếu
                if not is_present:
                    logger.warning(f"Component {temp_comp.id} có confidence thấp: {conf:.2f}, vis_score: {vis_score:.2f}")
            else:
                # Component KHÔNG được detect → THIẾU
                tx, ty, tw, th = temp_comp.box
                missing_areas.append(MissingArea(
                    id=f"missing_{temp_comp.id}",
                    description=temp_comp.label if hasattr(temp_comp, 'label') else "",
                    confidence=1.0,  # Chắc chắn thiếu vì không detect được
                    bbox=BoundingBox(x=tx - tw/2, y=ty - th/2, width=tw, height=th)
                ))

        is_defective = len(missing_areas) > 0
        total_comps = len(self._current_profile.components)
        found_comps = total_comps - len(missing_areas)
        missing_labels = [area.description for area in missing_areas if area.description]

        return InferenceResponse(
            isDefective=is_defective,
            confidence=1.0 if is_defective else 0.99,
            timestamp=datetime.utcnow(),
            boardName=self._current_profile.boardName,
            missingAreas=missing_areas,
            missingComponentLabels=missing_labels,
            notes=f"Kiểm tra: {found_comps}/{total_comps} linh kiện. (Matches: {len(matched_results)})"
        )