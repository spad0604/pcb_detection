# PCB Missing Component Inspector - Backend API

## 📋 Mô tả

Backend API cho hệ thống kiểm tra linh kiện thiếu trên PCB sử dụng **Template Matching + Statistical Anomaly Detection**.

### Công nghệ sử dụng
- **Framework**: FastAPI (Python 3.10+)
- **Computer Vision**: OpenCV, Pillow, NumPy
- **WebSocket**: Real-time camera streaming
- **CORS**: Hỗ trợ cross-origin requests

### Kiến trúc Model

Backend sử dụng **Template-based Anomaly Detection**:

1. **Training Phase**:
   - Thu thập ảnh PCB "đủ linh kiện" (OK samples)
   - Preprocessing: Loại bỏ background xanh/lục, crop vùng PCB, resize về 512x512
   - Tính toán template: `mean` và `std` từ tất cả ảnh OK
   - Lưu vào file `template_model.npz` và `template_meta.json`

2. **Inference Phase**:
   - Preprocess ảnh test giống training
   - So sánh với template bằng pixel difference và statistical threshold
   - Phát hiện vùng có sai lệch > threshold
   - Trả về: label (OK/DEFECTIVE), confidence, bounding boxes của vùng sai lệch

---

## 🚀 Cài đặt và Chạy

### Yêu cầu hệ thống
```bash
# Python 3.10 trở lên
python3 --version

# Camera (tùy chọn - có thể dùng ảnh tĩnh)
# Ubuntu/Linux: v4l2-ctl để kiểm tra camera
sudo apt install v4l-utils
v4l2-ctl --list-devices
```

### Cài đặt dependencies

```bash
cd Embedded/backend

# Tạo môi trường ảo (khuyến nghị)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Cài đặt packages
pip install -r requirements.txt
```

### Chạy server

```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Hoặc dùng script
./start_server.sh
```

Server chạy tại: `http://localhost:8000`

### Kiểm tra server

```bash
# Health check
curl http://localhost:8000/health

# API documentation (Swagger UI)
xdg-open http://localhost:8000/docs

# API documentation (ReDoc)
xdg-open http://localhost:8000/redoc
```

---

## 📡 API Endpoints

**Tất cả API đều nằm trong file `app/main.py`**

### 1. Health Check

**GET** `/health`

Kiểm tra trạng thái server.

**Response:**
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 2. Dataset Management

#### 2.1 Lấy danh sách dataset

**GET** `/api/dataset`

Trả về tất cả ảnh đã upload trong dataset.

**Response:**
```json
[
  {
    "id": "abc12345",
    "name": "pcb_ok_001.jpg",
    "label": "ok",
    "sizeBytes": 245678,
    "createdAt": "2024-12-02T15:30:00",
    "path": "/path/to/data/dataset/ok/abc12345_pcb_ok_001.jpg"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/dataset
```

#### 2.2 Upload ảnh vào dataset

**POST** `/api/dataset`

Upload ảnh PCB để training (ảnh "đủ linh kiện").

**Parameters (Form Data):**
- `label`: `"ok"` hoặc `"missing"` (thường dùng `"ok"` cho ảnh chuẩn)
- `file`: File ảnh (JPG, PNG, BMP, GIF)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/dataset" \
  -F "file=@pcb_ok_001.jpg" \
  -F "label=ok"
```

**Response:**
```json
{
  "id": "def67890",
  "name": "pcb_ok_001.jpg",
  "label": "ok",
  "sizeBytes": 245678,
  "createdAt": "2024-12-02T15:35:00",
  "path": "/path/to/data/dataset/ok/def67890_pcb_ok_001.jpg"
}
```

**Lưu ý:**
- Ảnh sẽ được lưu vào `data/dataset/{label}/`
- Metadata được lưu trong `data/dataset.json`
- Cần ít nhất 3 ảnh để train

---

### 3. Training

#### 3.1 Bắt đầu training

**POST** `/api/train`

Train template model từ dataset đã upload.

**Request Body (JSON):**
```json
{
  "boardName": "ESP32 DevKit v1",
  "epochs": 20,
  "testSplit": 0.2
}
```

**Parameters:**
- `boardName` (required): Tên mạch PCB để tracking
- `epochs`: Số epochs (không thực sự dùng trong template-based model)
- `testSplit`: Tỷ lệ validation data (0-1)

**Response:**
```json
{
  "jobId": "abc12345"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/train" \
  -H "Content-Type: application/json" \
  -d '{
    "boardName": "ESP32 Test Board",
    "epochs": 20,
    "testSplit": 0.2
  }'
```

#### 3.2 Kiểm tra trạng thái training

**GET** `/api/train/{job_id}`

Lấy thông tin training job.

**Response:**
```json
{
  "jobId": "abc12345",
  "status": "succeeded",
  "progress": 1.0,
  "message": "Hoàn tất xây template PCB 'ESP32 Test Board'",
  "metrics": {
    "board": "ESP32 Test Board",
    "samples": 10
  },
  "boardName": "ESP32 Test Board"
}
```

**Status values:**
- `idle`: Chưa bắt đầu
- `running`: Đang training
- `succeeded`: Hoàn thành
- `failed`: Lỗi

**Example:**
```bash
curl http://localhost:8000/api/train/abc12345
```

**Lưu ý:**
- Training sẽ tạo file `data/artifacts/template_model.npz` (chứa mean, std)
- Metadata lưu trong `data/artifacts/template_meta.json`
- Sau khi train xong, dataset sẽ được xóa tự động

---

### 4. Inference (Kiểm tra PCB)

**POST** `/api/inference`

Kiểm tra ảnh PCB có thiếu linh kiện không.

**Parameters (Form Data):**
- `file`: File ảnh PCB cần kiểm tra

**Request:**
```bash
curl -X POST "http://localhost:8000/api/inference" \
  -F "file=@pcb_test_001.jpg"
```

**Response:**
```json
{
  "isDefective": true,
  "confidence": 0.87,
  "timestamp": "2024-12-02T15:40:00",
  "missingAreas": [
    {
      "id": "region-1",
      "description": "Vùng lệch (214, 334) kích thước 114x14",
      "confidence": 0.65,
      "bbox": {
        "x": 0.41796875,
        "y": 0.65234375,
        "width": 0.22265625,
        "height": 0.02734375
      }
    },
    {
      "id": "region-2",
      "description": "Vùng lệch (336, 299) kích thước 8x25",
      "confidence": 0.58,
      "bbox": {
        "x": 0.65625,
        "y": 0.583984375,
        "width": 0.015625,
        "height": 0.048828125
      }
    }
  ],
  "notes": "PCB: ESP32 Test Board · Sai lệch 3.22%"
}
```

**Bounding Box Format:**
- Tọa độ normalized (0.0 - 1.0)
- `x`, `y`: Top-left corner
- `width`, `height`: Kích thước hộp
- Để vẽ lên ảnh: `pixel_x = bbox.x * image_width`

**Lưu ý:**
- Cần train trước khi inference (phải có file template)
- Nếu chưa train sẽ báo lỗi 400: "Chưa có template cho PCB"

---

### 5. Camera Stream (Real-time)

#### 5.1 Lấy frame từ camera

**GET** `/api/stream/frame`

Lấy 1 frame từ camera (JPEG).

**Response:**
- Content-Type: `image/jpeg`
- Binary JPEG data

**Example:**
```bash
# Lưu frame
curl http://localhost:8000/api/stream/frame --output frame.jpg

# Xem trong browser
xdg-open http://localhost:8000/api/stream/frame
```

**Fallback logic:**
1. Ưu tiên: Camera ngoài (index được detect tự động)
2. Backup: Ảnh từ dataset (nếu có)
3. Cuối cùng: Placeholder "Camera không khả dụng"

#### 5.2 MJPEG Stream (Video liên tục)

**GET** `/api/stream/mjpeg`

Stream video liên tục từ camera (30 FPS).

**Response:**
- Content-Type: `multipart/x-mixed-replace; boundary=frame`
- MJPEG stream

**Example:**
```bash
# Xem trong VLC hoặc browser
vlc http://localhost:8000/api/stream/mjpeg

# Hoặc mở trong browser
xdg-open http://localhost:8000/api/stream/mjpeg
```

**Lưu ý:**
- Endpoint này không tự động close, client cần disconnect khi không dùng
- FPS giới hạn ở 30 FPS để tránh quá tải

#### 5.3 WebSocket Stream

**WebSocket** `/api/stream/ws`

Real-time video stream qua WebSocket (độ trễ thấp hơn HTTP).

**Message Format:**
```json
{
  "type": "frame",
  "data": "<base64_encoded_jpeg>",
  "timestamp": 1701529800.123
}
```

**Client Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/stream/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'frame') {
    const img = document.getElementById('video');
    img.src = 'data:image/jpeg;base64,' + data.data;
  }
};

ws.onclose = () => console.log('WebSocket closed');
ws.onerror = (err) => console.error('WebSocket error:', err);
```

**Lưu ý:**
- WebSocket tự động reconnect nếu bị disconnect
- FPS: ~30 FPS
- Dùng cho Flutter Desktop app

#### 5.4 Phân tích camera real-time

**GET** `/api/stream/analyze`

Phân tích frame hiện tại từ camera và trả về kết quả inference.

**Response:**
```json
{
  "isDefective": false,
  "confidence": 0.94,
  "timestamp": "2024-12-02T15:45:00",
  "missingAreas": [],
  "notes": "PCB: ESP32 Test Board · Sai lệch 0.12%"
}
```

**Example:**
```bash
curl http://localhost:8000/api/stream/analyze
```

**Lưu ý:**
- Cần có template đã train
- Nếu không có camera hoặc template sẽ báo lỗi 404

---

## 📁 Cấu trúc API trong code

Tất cả API endpoints được định nghĩa trong **`app/main.py`**:

```python
# app/main.py

# Health check
@app.get("/health")
async def health_check() -> dict[str, str]

# Dataset APIs
@app.get("/api/dataset")
async def list_dataset() -> list[dict]

@app.post("/api/dataset")
async def upload_dataset(label: str, file: UploadFile) -> dict

# Training APIs
@app.post("/api/train")
async def start_training(request: TrainRequest) -> dict[str, str]

@app.get("/api/train/{job_id}")
async def training_status(job_id: str) -> dict

# Inference APIs
@app.post("/api/inference")
async def run_inference(file: UploadFile) -> dict

# Camera Stream APIs
@app.get("/api/stream/frame")
async def get_stream_frame() -> Response

@app.get("/api/stream/mjpeg")
async def get_mjpeg_stream(request: Request) -> StreamingResponse

@app.websocket("/api/stream/ws")
async def websocket_stream(websocket: WebSocket)

@app.get("/api/stream/analyze")
async def analyze_stream_frame() -> dict
```

### Services được sử dụng

```python
# Khởi tạo services
dataset_service = DatasetService(settings)
training_service = TrainingService(settings, dataset_service)
inference_service = InferenceService(settings)
camera_service = CameraService(settings, camera_index=4)
```

---

## 🔧 Cấu hình Camera

### Tự động detect camera

Backend tự động phát hiện camera ngoài và bỏ qua:
- Camera laptop (index 0)
- Camera hồng ngoại (IR camera)

### Thay đổi camera index

**Cách 1: Environment variable**
```bash
export CAMERA_INDEX=2
uvicorn app.main:app --reload
```

**Cách 2: Sửa trong code**
```python
# app/main.py, dòng ~25
camera_index = 2  # Thay đổi index này
camera_service = CameraService(settings, camera_index=camera_index)
```

### Kiểm tra cameras có sẵn

```bash
# Linux
v4l2-ctl --list-devices

# Hoặc dùng Python
python3 -c "
import cv2
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'Camera {i}: Available')
        cap.release()
"
```

---

## 🧪 Testing Workflow

### 1. Khởi động server
```bash
cd Embedded/backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. Upload dataset (3-10 ảnh "đủ linh kiện")
```bash
for img in ok_*.jpg; do
  curl -X POST "http://localhost:8000/api/dataset" \
    -F "file=@$img" \
    -F "label=ok"
done
```

### 3. Kiểm tra dataset đã upload
```bash
curl http://localhost:8000/api/dataset | jq
```

### 4. Train template
```bash
curl -X POST "http://localhost:8000/api/train" \
  -H "Content-Type: application/json" \
  -d '{
    "boardName": "My PCB Board",
    "epochs": 20,
    "testSplit": 0.2
  }'

# Lấy jobId từ response, ví dụ: "abc12345"
```

### 5. Kiểm tra training status
```bash
# Thay abc12345 bằng jobId thực tế
curl http://localhost:8000/api/train/abc12345
```

### 6. Test inference
```bash
curl -X POST "http://localhost:8000/api/inference" \
  -F "file=@test_pcb.jpg" | jq
```

### 7. Test camera stream
```bash
# Frame đơn
curl http://localhost:8000/api/stream/frame --output test_frame.jpg

# Analysis
curl http://localhost:8000/api/stream/analyze | jq
```

---

## 📊 Data Files

### Dataset metadata
```bash
cat data/dataset.json
```

Format:
```json
[
  {
    "id": "abc123",
    "name": "pcb_ok_001.jpg",
    "label": "ok",
    "sizeBytes": 245678,
    "createdAt": "2024-12-02T15:30:00.000Z",
    "path": "data/dataset/ok/abc123_pcb_ok_001.jpg"
  }
]
```

### Template model (sau training)
```bash
# NumPy compressed archive
ls -lh data/artifacts/template_model.npz

# Metadata
cat data/artifacts/template_meta.json
```

Template metadata format:
```json
{
  "boardName": "ESP32 Test Board",
  "trainedAt": "2024-12-02T15:35:00.000Z",
  "numSamples": 10,
  "templateSize": {
    "width": 512,
    "height": 512
  },
  "sourceImages": [
    "data/dataset/ok/abc123_pcb_ok_001.jpg"
  ]
}
```

---

## 🐛 Troubleshooting

### API Error: "Chưa có template cho PCB"

**Nguyên nhân:** Chưa train hoặc file template bị xóa

**Giải pháp:**
```bash
# Kiểm tra file template
ls -la data/artifacts/template_model.npz

# Nếu không có, upload dataset và train lại
curl -X POST "http://localhost:8000/api/train" \
  -H "Content-Type: application/json" \
  -d '{"boardName": "Test"}'
```

### Camera không hoạt động

**Kiểm tra:**
```bash
# List cameras
v4l2-ctl --list-devices

# Test với OpenCV
python3 -c "import cv2; print(cv2.VideoCapture(0).read())"
```

**Giải pháp:**
```bash
# Thử camera index khác
export CAMERA_INDEX=2
uvicorn app.main:app --reload
```

### Dataset trống khi list

**Nguyên nhân:** File dataset.json bị hỏng hoặc chưa upload

**Giải pháp:**
```bash
# Reset dataset
rm -f data/dataset.json
echo "[]" > data/dataset.json

# Upload lại
curl -X POST "http://localhost:8000/api/dataset" \
  -F "file=@test.jpg" -F "label=ok"
```

### Training bị lỗi: "Cần ít nhất 3 ảnh"

**Giải pháp:**
```bash
# Upload thêm ảnh
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/dataset" \
    -F "file=@ok_sample_$i.jpg" -F "label=ok"
done
```

---

## 🔐 Security Notes

⚠️ **Backend này chỉ dùng cho local/development**:

- ❌ Không có authentication
- ❌ CORS cho phép tất cả origins
- ❌ Không giới hạn file size
- ❌ Không rate limiting

**Để deploy production:**
1. Thêm API key authentication
2. Giới hạn CORS origins
3. Thêm file size limit (max 10MB)
4. Rate limiting cho upload/inference endpoints
5. HTTPS với SSL certificate

---

## 📈 Performance

### Inference Speed
- **CPU**: ~200-300ms per image
- **GPU** (nếu có): ~50-100ms

### Camera Stream
- **HTTP Polling**: 5-10 FPS
- **WebSocket**: 15-30 FPS
- **MJPEG Stream**: 30 FPS (smooth nhất)

### Memory Usage
- Baseline: ~200MB
- With camera: ~300-400MB
- Training: ~500MB-1GB

---

## 📞 API Summary Table

| Method | Endpoint | Description | Requires Template |
|--------|----------|-------------|-------------------|
| GET | `/health` | Health check | ❌ |
| GET | `/api/dataset` | List uploaded images | ❌ |
| POST | `/api/dataset` | Upload image | ❌ |
| POST | `/api/train` | Start training | ❌ |
| GET | `/api/train/{job_id}` | Check training status | ❌ |
| POST | `/api/inference` | Analyze image | ✅ |
| GET | `/api/stream/frame` | Get single frame | ❌ |
| GET | `/api/stream/mjpeg` | Video stream | ❌ |
| WS | `/api/stream/ws` | WebSocket stream | ❌ |
| GET | `/api/stream/analyze` | Analyze camera frame | ✅ |

---

## 🎯 Quick Start Example

```bash
# 1. Start server
cd Embedded/backend
uvicorn app.main:app --reload

# 2. Upload 5 OK samples
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/dataset" \
    -F "file=@ok_$i.jpg" -F "label=ok"
done

# 3. Train
curl -X POST "http://localhost:8000/api/train" \
  -H "Content-Type: application/json" \
  -d '{"boardName": "Test PCB"}'

# 4. Wait for training (~5-10 seconds)
sleep 10

# 5. Test inference
curl -X POST "http://localhost:8000/api/inference" \
  -F "file=@test.jpg" | jq

# Done! 🎉
```

---

## 📝 Notes

- API documentation có sẵn tại: `http://localhost:8000/docs`
- Interactive API testing: `http://localhost:8000/docs#/`
- Alternative docs: `http://localhost:8000/redoc`
- Code API nằm trong: `app/main.py` (1 file duy nhất, dễ đọc)

---

**Last updated:** December 2, 2025
