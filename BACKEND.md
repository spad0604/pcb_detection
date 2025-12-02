# PCB Missing Component Inspector - Backend API

## 📋 Mô tả

Backend API cho hệ thống kiểm tra linh kiện thiếu trên PCB sử dụng **Template Matching + Statistical Anomaly Detection**.

### Công nghệ sử dụng
- **Framework**: FastAPI (Python 3.10+)
- **Computer Vision**: OpenCV, Pillow, scikit-image
- **Machine Learning**: NumPy-based statistical model (không dùng deep learning)
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
   - So sánh với template bằng:
     - **Structural Similarity (SSIM)**: Đo độ tương đồng cấu trúc
     - **Pixel Difference**: Tính khoảng cách pixel-wise
     - **Statistical Threshold**: Phát hiện vùng có sai lệch > 2*sigma
   - Trả về: label (OK/MISSING), confidence, bounding boxes của vùng sai lệch

3. **Feature Extraction**:
   - Mean RGB: Giá trị trung bình mỗi kênh màu
   - Standard Deviation: Độ biến thiên
   - Contrast: Độ tương phản grayscale
   - Vector đặc trưng: `[mean_R, mean_G, mean_B, std_all, contrast]`

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

### 1. Health Check

**GET** `/health`

Kiểm tra trạng thái server.

**Response:**
```json
{
  "status": "healthy",
  "backend_version": "1.0.0",
  "timestamp": "2024-12-02T15:30:00"
}
```

---

### 2. Dataset Management

#### 2.1 Upload ảnh vào dataset

**POST** `/api/dataset/upload`

Upload ảnh PCB để training. Ảnh sẽ được preprocess (remove background, crop PCB).

**Parameters:**
- `file`: ảnh PCB (multipart/form-data)
- `label`: `"ok"` hoặc `"missing"` (default: `"ok"`)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/dataset/upload" \
  -F "file=@pcb_ok_001.jpg" \
  -F "label=ok"
```

**Response:**
```json
{
  "id": "abc123def456",
  "path": "data/dataset/ok_abc123def456.jpg",
  "label": "ok",
  "uploaded_at": "2024-12-02T15:30:00"
}
```

#### 2.2 Lấy danh sách dataset

**GET** `/api/dataset`

**Response:**
```json
{
  "total": 25,
  "samples": [
    {
      "id": "abc123",
      "path": "data/dataset/ok_abc123.jpg",
      "label": "ok",
      "uploaded_at": "2024-12-02T15:30:00"
    }
  ],
  "distribution": {
    "ok": 20,
    "missing": 5
  }
}
```

#### 2.3 Xóa sample

**DELETE** `/api/dataset/{sample_id}`

**Response:**
```json
{
  "message": "Đã xóa sample abc123"
}
```

---

### 3. Training

#### 3.1 Bắt đầu training

**POST** `/api/training/start`

Train template model từ dataset.

**Request Body:**
```json
{
  "board_name": "ESP32 DevKit v1",
  "epochs": 20,
  "test_split": 0.2
}
```

**Response:**
```json
{
  "job_id": "train_20241202_153000",
  "status": "started",
  "message": "Đã bắt đầu training"
}
```

#### 3.2 Kiểm tra trạng thái training

**GET** `/api/training/status/{job_id}`

**Response:**
```json
{
  "job_id": "train_20241202_153000",
  "status": "training",
  "progress": 0.65,
  "current_epoch": 13,
  "total_epochs": 20,
  "metrics": {
    "train_accuracy": 0.95,
    "val_accuracy": 0.88
  },
  "message": "Epoch 13/20"
}
```

**Các status:**
- `idle`: Chưa train
- `started`: Đã khởi động
- `training`: Đang train
- `completed`: Hoàn thành
- `failed`: Lỗi

---

### 4. Inference (Kiểm tra PCB)

#### 4.1 Upload ảnh để kiểm tra

**POST** `/api/inference/upload`

Kiểm tra ảnh PCB có thiếu linh kiện không.

**Parameters:**
- `file`: ảnh PCB cần kiểm tra

**Request:**
```bash
curl -X POST "http://localhost:8000/api/inference/upload" \
  -F "file=@pcb_test_001.jpg"
```

**Response:**
```json
{
  "prediction": "missing",
  "confidence": 0.87,
  "processing_time_ms": 234,
  "missing_areas": [
    {
      "name": "Vùng lệch (214, 334) kích thước 114x14",
      "confidence": 0.92,
      "bbox": {
        "x": 0.41796875,
        "y": 0.65234375,
        "width": 0.22265625,
        "height": 0.02734375
      }
    }
  ],
  "details": {
    "board_name": "ESP32 DevKit v1",
    "error_percentage": 3.22
  }
}
```

**Bounding Box Format:**
- Tọa độ normalized (0.0 - 1.0)
- `x`, `y`: Top-left corner
- `width`, `height`: Kích thước hộp

---

### 5. Camera Stream (Real-time)

#### 5.1 Lấy frame từ camera

**GET** `/api/stream/frame`

Lấy 1 frame từ camera (MJPEG).

**Response:**
- Content-Type: `image/jpeg`
- Binary JPEG data

**Request:**
```bash
curl http://localhost:8000/api/stream/frame --output frame.jpg
```

#### 5.2 WebSocket stream

**WebSocket** `/api/stream/ws`

Real-time video stream qua WebSocket.

**Message Format:**
```json
{
  "type": "frame",
  "data": "<base64_encoded_jpeg>",
  "timestamp": "2024-12-02T15:30:00"
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
```

#### 5.3 Phân tích camera real-time

**GET** `/api/stream/analyze`

Phân tích frame hiện tại từ camera.

**Response:**
```json
{
  "prediction": "ok",
  "confidence": 0.94,
  "missing_areas": [],
  "details": {
    "board_name": "ESP32 DevKit v1",
    "error_percentage": 0.0
  }
}
```

#### 5.4 Liệt kê cameras

**GET** `/api/cameras`

**Response:**
```json
{
  "cameras": [
    {
      "index": 0,
      "name": "Integrated Camera",
      "type": "laptop",
      "resolution": "1280x720",
      "fps": 30,
      "available": true
    },
    {
      "index": 2,
      "name": "Logitech Webcam C920",
      "type": "external",
      "resolution": "1920x1080",
      "fps": 30,
      "available": true
    }
  ],
  "current": 2,
  "total": 2
}
```

#### 5.5 Chuyển camera

**POST** `/api/cameras/switch/{camera_index}`

**Response:**
```json
{
  "success": true,
  "message": "Đã chuyển sang camera 2",
  "current_camera": 2
}
```

---

## 📁 Cấu trúc thư mục

```
Embedded/backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── models/
│   │   └── dto.py             # Data Transfer Objects
│   ├── routes/
│   │   ├── dataset.py         # Dataset management APIs
│   │   ├── training.py        # Training APIs
│   │   ├── inference.py       # Inference APIs
│   │   └── stream.py          # Camera stream APIs
│   ├── services/
│   │   ├── camera_service.py  # Camera capture & analysis
│   │   ├── dataset_service.py # Dataset CRUD operations
│   │   ├── training_service.py# Training orchestration
│   │   ├── inference_service.py# Inference engine
│   │   └── feature_extractor.py# Feature extraction
│   └── utils/
│       └── image_processing.py # Preprocessing pipeline
├── data/
│   ├── dataset/               # Training images (auto-created)
│   ├── dataset.json          # Dataset metadata
│   └── artifacts/
│       ├── template_model.npz # Trained template (mean, std)
│       └── template_meta.json # Training metadata
├── requirements.txt
└── README.md
```

---

## 🔧 Cấu hình

### Camera Settings

File: `app/services/camera_service.py`

```python
# Độ phân giải camera
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 30

# Index camera (0=laptop, 2=external thường)
DEFAULT_CAMERA_INDEX = 0
```

### Image Preprocessing

File: `app/utils/image_processing.py`

```python
# Kích thước resize cho training/inference
TARGET_SIZE = (512, 512)

# Màu background cần loại bỏ (HSV ranges)
GREEN_BG_LOWER = [35, 40, 40]   # Xanh lá
GREEN_BG_UPPER = [85, 255, 255]
BLUE_BG_LOWER = [90, 50, 50]    # Xanh dương
BLUE_BG_UPPER = [130, 255, 255]
```

### Training Parameters

```python
# Mặc định trong API request
{
  "epochs": 20,           # Không thực sự dùng (template-based)
  "test_split": 0.2,      # 20% data để validation
  "board_name": "..."     # Tên PCB để tracking
}
```

---

## 🧪 Testing

### 1. Test health endpoint

```bash
curl http://localhost:8000/health
```

### 2. Test upload dataset

```bash
# Upload ảnh OK
curl -X POST "http://localhost:8000/api/dataset/upload" \
  -F "file=@test_ok.jpg" \
  -F "label=ok"

# Upload ảnh MISSING
curl -X POST "http://localhost:8000/api/dataset/upload" \
  -F "file=@test_missing.jpg" \
  -F "label=missing"
```

### 3. Test training

```bash
curl -X POST "http://localhost:8000/api/training/start" \
  -H "Content-Type: application/json" \
  -d '{
    "board_name": "ESP32 Test",
    "epochs": 10,
    "test_split": 0.2
  }'
```

### 4. Test inference

```bash
curl -X POST "http://localhost:8000/api/inference/upload" \
  -F "file=@test_pcb.jpg"
```

### 5. Test camera

```bash
# Lấy 1 frame
curl http://localhost:8000/api/stream/frame --output test_frame.jpg

# Phân tích frame
curl http://localhost:8000/api/stream/analyze
```

---

## 🐛 Troubleshooting

### Camera không hoạt động

```bash
# Kiểm tra camera có sẵn không
v4l2-ctl --list-devices

# Test camera với OpenCV
python3 -c "import cv2; print(cv2.VideoCapture(0).read())"

# Thử camera index khác (2, 4, 6...)
curl http://localhost:8000/api/cameras
```

### Lỗi "No module named 'cv2'"

```bash
pip install opencv-python
# Hoặc
pip install opencv-python-headless  # Không cần GUI
```

### Template model không tồn tại

```bash
# Training tạo file này tự động
ls -la data/artifacts/template_model.npz

# Nếu không có, cần train lại
curl -X POST "http://localhost:8000/api/training/start" \
  -H "Content-Type: application/json" \
  -d '{"board_name": "Test"}'
```

### Dataset trống

```bash
# Kiểm tra dataset
cat data/dataset.json

# Upload ít nhất 5 ảnh OK để train
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/dataset/upload" \
    -F "file=@ok_sample_$i.jpg" \
    -F "label=ok"
done
```

---

## 📊 Performance

### Inference Speed
- **CPU (Intel i5)**: ~200-300ms per image
- **GPU (optional)**: ~50-100ms per image

### Camera Stream
- **HTTP Polling**: ~5-10 FPS (có thể lag)
- **WebSocket**: ~15-30 FPS (smooth)

### Memory Usage
- **Baseline**: ~200MB
- **With camera**: ~300-400MB
- **During training**: ~500MB-1GB

---

## 🔐 Security Notes

- Backend **không có authentication** - chỉ dùng local/internal network
- CORS enabled cho tất cả origins (`allow_origins=["*"]`)
- Không validate file upload size - có thể bị DoS
- **Production**: thêm API key, rate limiting, file size limit

---

## 📝 Changelog

### v1.0.0 (2024-12-02)
- ✅ Template-based anomaly detection
- ✅ Camera streaming (HTTP + WebSocket)
- ✅ Multi-camera support
- ✅ Background removal (green/blue)
- ✅ Bounding box detection
- ✅ FastAPI with Swagger docs

---

## 👥 Contributors

- **Backend API**: FastAPI + OpenCV
- **Model**: Template Matching + Statistical Analysis
- **Camera**: OpenCV VideoCapture

---

## 📄 License

MIT License - Free to use and modify.

---

## 🆘 Support

Nếu có vấn đề:

1. Check logs: Backend sẽ in chi tiết lỗi ra console
2. Check API docs: `http://localhost:8000/docs`
3. Test từng endpoint riêng lẻ với `curl`
4. Xem file `data/dataset.json` và `data/artifacts/` để debug

**Contact**: Xem file [`HUONG_DAN_CHAY.md`](HUONG_DAN_CHAY.md ) để biết thêm chi tiết setup.