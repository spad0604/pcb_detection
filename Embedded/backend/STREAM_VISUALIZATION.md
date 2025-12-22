# Real-time Detection Visualization trong Stream

## Luồng hoạt động

```
Arduino phát hiện mạch (EVENT:BOARD_AT_CAMERA)
  ↓
Backend chụp frame + chạy YOLO inference
  ↓
Vẽ bounding boxes (đỏ cho missing, xanh cho OK) lên frame
  ↓
Lưu annotated frame vào LineController.last_annotated_frame
  ↓
Stream endpoints ưu tiên trả annotated frame
  ↓
Frontend stream thấy real-time detection với boxes + labels
```

## Các endpoint stream đã cập nhật

### 1. GET /api/stream/frame

**Độ ưu tiên:**
1. **Annotated frame** (có bounding boxes) từ `line_controller.get_annotated_frame()`
2. Camera frame thường từ `camera_service.get_frame()`
3. Placeholder frame

**Cách hoạt động:**
- Khi Arduino phát hiện mạch → backend inference → vẽ boxes → lưu vào `last_annotated_frame`
- Stream endpoint sẽ trả về frame này **thay vì raw camera**
- Frontend thấy ngay bounding boxes màu đỏ cho linh kiện thiếu
- Annotated frame được cache cho đến khi có detection mới

### 2. GET /api/stream/mjpeg

**Tương tự**, ưu tiên annotated frame trong MJPEG stream.

## Visualization details

### Bounding Boxes

**Missing components (màu đỏ):**
```python
cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)  # BGR: Red
cv2.putText(frame, "MISSING (1.00)", (x1, y1-5), 
           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
```

### Header Text

**Verdict (góc trên trái):**
- "THIẾU LINH KIỆN" (đỏ) nếu defective
- "ĐỦ LINH KIỆN" (xanh) nếu OK
- Board name hiển thị dòng 2

```python
cv2.putText(frame, "THIẾU LINH KIỆN", (10, 30), 
           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
cv2.putText(frame, "LM2596", (10, 60), 
           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
```

## Frontend Integration

### Image/Video widget

Frontend **không cần thay đổi gì**, chỉ cần hiển thị stream như bình thường:

```dart
// Flutter
Image.network(
  'http://localhost:8000/api/stream/frame',
  fit: BoxFit.contain,
)

// Hoặc MJPEG stream
Image.network(
  'http://localhost:8000/api/stream/mjpeg',
  fit: BoxFit.contain,
)
```

### Kết quả

- Stream ban đầu: raw camera feed
- Khi mạch vào camera position: 
  - Arduino → EVENT → Backend inference
  - Frame tự động chuyển sang **annotated version** với boxes màu đỏ
  - User thấy ngay linh kiện nào thiếu
- Annotated frame hiển thị cho đến khi có mạch mới

## Code Implementation

### InferenceService.draw_detection_boxes()

```python
def draw_detection_boxes(self, image: np.ndarray, response: InferenceResponse) -> bytes:
    """Vẽ bounding boxes + labels lên frame và trả về JPEG bytes."""
    annotated = image.copy()
    h, w = annotated.shape[:2]
    
    # Vẽ missing areas (RED)
    for area in response.missingAreas:
        x1 = int(area.bbox.x * w)
        y1 = int(area.bbox.y * h)
        x2 = int((area.bbox.x + area.bbox.width) * w)
        y2 = int((area.bbox.y + area.bbox.height) * h)
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{area.description} ({area.confidence:.2f})"
        cv2.putText(annotated, label, (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # Vẽ header với verdict
    verdict = "THIẾU LINH KIỆN" if response.isDefective else "ĐỦ LINH KIỆN"
    color = (0, 0, 255) if response.isDefective else (0, 255, 0)
    cv2.putText(annotated, verdict, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
    
    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', annotated)
    return buffer.tobytes()
```

### LineController._auto_detect()

```python
async def _auto_detect(self) -> None:
    # Lấy frame từ camera
    frame = await asyncio.to_thread(self.camera_service.get_frame)
    
    # Decode để vẽ boxes
    nparr = np.frombuffer(frame, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Chạy inference
    result = await self.inference_service.analyze_bytes(frame)
    self.last_result = result
    
    # Vẽ bounding boxes lên frame
    self.last_annotated_frame = await asyncio.to_thread(
        self.inference_service.draw_detection_boxes, img, result
    )
    
    # Gửi kết quả về Arduino
    command = "CMD:RESULT:NG" if result.isDefective else "CMD:RESULT:OK"
    self.send_command(command)
```

## Tóm tắt

1. **Tự động visualization**: Không cần API riêng, stream endpoints tự động ưu tiên annotated frame
2. **Real-time feedback**: Frontend stream thấy ngay bounding boxes khi có detection
3. **Zero frontend changes**: Widget hiển thị stream giữ nguyên, backend tự động inject annotated frame
4. **Color coding**: Đỏ = missing, Xanh = OK, dễ nhìn
5. **Persistent display**: Annotated frame hiển thị cho đến detection mới (không bị flicker)
