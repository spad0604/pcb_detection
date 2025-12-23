from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from fastapi import UploadFile
from ultralytics import YOLO

from ..core.config import Settings
from ..models.dto import BoundingBox, InferenceResponse, MissingArea, BoardProfile

class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        
        # Load Model YOLO (Logic giống collab: load best.pt)
        self.model_path = settings.artifacts_dir / "best.pt"
        if not self.model_path.exists():
             print("Warning: best.pt not found, using yolov8n.pt fallback")
             self.model = YOLO("yolov8n.pt") 
        else:
             self.model = YOLO(str(self.model_path))
             
        # Cache profile & SIFT data
        self._current_profile: Optional[BoardProfile] = None
        self._ref_image_cache: Optional[np.ndarray] = None
        
        self._sift = cv2.SIFT_create()
        self._ref_kp = None 
        self._ref_des = None 

    def _create_pcb_mask(self, img: np.ndarray) -> np.ndarray:
        """Logic tạo mask giữ nguyên từ collab.py"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

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
                if ref_path.exists():
                    self._ref_image_cache = cv2.imread(str(ref_path))
                    
                    # Pre-calculate SIFT for reference image
                    mask_ref = self._create_pcb_mask(self._ref_image_cache)
                    gray_ref = cv2.cvtColor(self._ref_image_cache, cv2.COLOR_BGR2GRAY)
                    self._ref_kp, self._ref_des = self._sift.detectAndCompute(gray_ref, mask_ref)
                    print(f"InferenceService: Loaded profile '{profile_name}'")
                    
        except Exception as e:
            print(f"Error loading profile: {e}")

    async def run(self, upload: UploadFile) -> InferenceResponse:
        contents = await upload.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self._analyze(img)

    async def analyze_bytes(self, data: bytes) -> InferenceResponse:
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self._analyze(img)

    def _align_image(self, target_img: np.ndarray) -> np.ndarray:
        """
        Logic Align giữ nguyên từ collab.py: 
        Rotation check -> SIFT -> Affine Partial
        """
        if self._ref_image_cache is None or self._ref_des is None: 
            return target_img
            
        h_ref, w_ref = self._ref_image_cache.shape[:2]
        h_tgt, w_tgt = target_img.shape[:2]
        
        # 1. Rotation logic
        if (w_ref > h_ref) and (h_tgt > w_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)
        elif (h_ref > w_ref) and (w_tgt > h_tgt):
            target_img = cv2.rotate(target_img, cv2.ROTATE_90_CLOCKWISE)

        # 2. SIFT Matching
        mask_tgt = self._create_pcb_mask(target_img)
        gray_tgt = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        kp2, des2 = self._sift.detectAndCompute(gray_tgt, mask_tgt)
        
        if des2 is None or len(kp2) < 5: return target_img
        
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(self._ref_des, des2, k=2)
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance: good.append(m)
            
        if len(good) > 10:
            src_pts = np.float32([self._ref_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            
            # 3. Affine Partial (Xoay + Dịch + Scale)
            M, inliers = cv2.estimateAffinePartial2D(dst_pts, src_pts)
            if M is not None:
                return cv2.warpAffine(target_img, M, (w_ref, h_ref), flags=cv2.INTER_CUBIC)
                
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
        """
        Hàm chính thực hiện logic phân tích.
        Sử dụng logic 'Local Greedy' và các ngưỡng từ collab.py.
        """
        # Reload profile if needed
        if self._current_profile is None:
            self._load_active_profile()
            
        if self._current_profile is None or self._ref_image_cache is None:
             return InferenceResponse(
                 isDefective=False, confidence=0.0, timestamp=datetime.utcnow(), 
                 boardName="Unknown", notes="Chưa có profile nào được train."
             )

        # 1. Alignment
        aligned_img = self._align_image(image)
        h, w = aligned_img.shape[:2]

        # 2. Detect YOLO
        results = self.model(aligned_img, verbose=False, conf=0.25)
        
        detected_candidates = []
        for r in results:
            for i, box in enumerate(r.boxes):
                detected_candidates.append({
                    'id': i,
                    'box': box.xywhn[0].tolist(), # [x, y, w, h] normalized
                    'conf': float(box.conf[0]),
                    'is_used': False
                })

        # 3. MATCHING LOGIC
        missing_areas = []
        total_comps = len(self._current_profile.components)
        
        # Duyệt qua từng linh kiện mẫu (Template)
        for temp_comp in self._current_profile.components:
            tx, ty, tw, th = temp_comp.box
            
            matched_candidate = None
            best_score = -999

            for candidate in detected_candidates:
                if candidate['is_used']:
                    continue

                iou = self._calculate_iou(temp_comp.box, candidate['box'])
                dx, dy, _, _ = candidate['box']
                dist = np.sqrt((tx - dx)**2 + (ty - dy)**2)

                # ĐIỀU KIỆN KHỚP 
                is_match = (iou > 0.01) or (dist < 0.06)

                if is_match:
                    score = iou + (1.0 - dist)
                    if score > best_score:
                        best_score = score
                        matched_candidate = candidate

            # Kiểm tra kết quả khớp
            yolo_found = False
            if matched_candidate:
                yolo_found = True
                matched_candidate['is_used'] = True 
            
            is_present = False
            
            if yolo_found:
                matched_box = matched_candidate['box']
                matched_conf = matched_candidate['conf']
                
                # Verify Visual
                vis_score = self._verify_visual(aligned_img, matched_box)

                # LOGIC PHÁN ĐOÁN 
                if vis_score > 0.15:
                    is_present = True # OK
                elif matched_conf > 0.3: 
                    is_present = True # OK
                else:
                    is_present = False 

            # Xử lý kết quả để trả về API
            if yolo_found and is_present:

                pass
            
            elif yolo_found and not is_present:
                
                missing_areas.append(MissingArea(
                    id=f"bad_{temp_comp.id}",
                    description="Lỗi/Sai linh kiện",
                    confidence=matched_candidate['conf'],
                    bbox=BoundingBox(x=tx - tw/2, y=ty - th/2, width=tw, height=th)
                ))
            
            else:
                # MISSING
                missing_areas.append(MissingArea(
                    id=f"missing_{temp_comp.id}",
                    description="Thiếu linh kiện",
                    confidence=1.0,
                    bbox=BoundingBox(x=tx - tw/2, y=ty - th/2, width=tw, height=th)
                ))

        # Tổng hợp kết quả
        is_defective = len(missing_areas) > 0
        found_comps = total_comps - len(missing_areas)

        return InferenceResponse(
            isDefective=is_defective,
            confidence=1.0 if is_defective else 0.99,
            timestamp=datetime.utcnow(),
            boardName=self._current_profile.boardName,
            missingAreas=missing_areas,
            notes=f"Đã kiểm tra: {found_comps}/{total_comps} linh kiện."
        )