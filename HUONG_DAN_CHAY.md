# Hướng Dẫn Chạy Dự Án PCB Detection

Dự án này gồm 2 phần chính:
- **Backend**: API server FastAPI (Python) để xử lý phân loại PCB
- **Frontend**: Ứng dụng Flutter Desktop để giao diện người dùng

## Yêu Cầu Hệ Thống

### Backend:
- Python 3.8 trở lên
- pip (Python package manager)

### Frontend:
- Flutter SDK 3.9.2 trở lên
- Dart SDK

## Cách Chạy Dự Án

### Bước 1: Chạy Backend (API Server)

1. **Di chuyển vào thư mục backend:**
```bash
cd Embedded/backend
```

2. **Tạo môi trường ảo Python (khuyến nghị):**
```bash
python3 -m venv venv
source venv/bin/activate  # Trên Linux/Mac
# hoặc
venv\Scripts\activate  # Trên Windows
```

3. **Cài đặt các dependencies:**
```bash
pip install -r requirements.txt
```

**Lưu ý:** Package `opencv-python` sẽ được cài đặt để hỗ trợ stream từ camera laptop. Nếu có vấn đề với camera, hệ thống sẽ tự động fallback về dataset hoặc placeholder.

4. **Chạy server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: `http://127.0.0.1:8000`

**Kiểm tra server đã chạy:**
- Mở trình duyệt và truy cập: `http://127.0.0.1:8000/health`
- Hoặc xem API docs tại: `http://127.0.0.1:8000/docs`

### Bước 2: Chạy Frontend (Flutter App)

1. **Mở terminal mới và di chuyển vào thư mục Desktop:**
```bash
cd Desktop
```

2. **Cài đặt dependencies Flutter:**
```bash
flutter pub get
```

3. **Chạy ứng dụng:**
```bash
flutter run -d linux  # Cho Linux
# hoặc
flutter run -d windows  # Cho Windows
# hoặc
flutter run -d macos  # Cho macOS
```

**Lưu ý:** 
- Ứng dụng Flutter cần kết nối đến backend tại `http://127.0.0.1:8000` (mặc định trong code)
- Đảm bảo backend đã chạy trước khi khởi động frontend

## Sử Dụng Ứng Dụng

1. **Upload dữ liệu mẫu:**
   - Trong giao diện, chọn ảnh PCB và nhãn (ok/missing)
   - Upload nhiều mẫu để có dataset đầy đủ

2. **Training model (theo từng mạch PCB):**
   - Nhập tên PCB (ví dụ: "PCB nguồn 12V")
   - Upload **chỉ các ảnh chuẩn (đủ linh kiện)** của PCB đó (càng nhiều góc, kết quả càng ổn định)
   - Đặt số epochs và test split (dùng mặc định cũng được)
   - Bấm **Train ngay** để backend xây dựng template (mean image + sai lệch) cho PCB
   - Template được lưu tại: `Embedded/backend/data/artifacts/template_model.npz`
   - Sau khi train xong thành công, toàn bộ dataset đã dùng sẽ được xóa để sẵn sàng train mạch khác

3. **Giám sát realtime & inference:**
   - Camera stream được phân tích liên tục; panel “Live conveyor feed” hiển thị trạng thái (OK / Sai lệch) và khoanh vùng ngay trên video
   - Nếu cần kiểm tra thủ công, vẫn có thể gọi API `/api/inference` (upload ảnh riêng lẻ)

## Cấu Trúc Thư Mục

```
pcb_detection/
├── Embedded/
│   └── backend/          # FastAPI backend
│       ├── app/
│       │   ├── main.py   # Entry point của API
│       │   └── ...
│       └── requirements.txt
├── Desktop/              # Flutter frontend
│   ├── lib/
│   │   └── app/
│   └── pubspec.yaml
└── data/                 # Dữ liệu và model (tự động tạo)
    └── artifacts/        # Model được lưu ở đây
```

## Xử Lý Lỗi

### Backend không chạy được:
- Kiểm tra Python version: `python3 --version`
- Kiểm tra đã cài đặt dependencies: `pip list`
- Kiểm tra port 8000 có bị chiếm không: `lsof -i :8000` (Linux/Mac) hoặc `netstat -ano | findstr :8000` (Windows)

### Frontend không kết nối được backend:
- Kiểm tra backend đã chạy chưa
- Kiểm tra URL trong `lib/app/services/api_service.dart` có đúng không
- Kiểm tra firewall không chặn port 8000

### Lỗi Flutter:
- Chạy `flutter doctor` để kiểm tra môi trường
- Chạy `flutter clean` và `flutter pub get` lại
- Đảm bảo Flutter SDK đã được cài đặt đúng

## API Endpoints

- `GET /health` - Kiểm tra server
- `GET /api/dataset` - Lấy danh sách mẫu dataset
- `POST /api/dataset` - Upload mẫu mới (label: ok/missing, file: image)
- `POST /api/train` - Bắt đầu training (tham số: `boardName`, `epochs`, `testSplit`)
- `GET /api/train/{job_id}` - Lấy trạng thái training job
- `POST /api/inference` - Phân loại PCB dựa trên chênh lệch so với template
- `GET /api/stream/frame` - Lấy frame đơn lẻ từ video stream (ưu tiên: camera laptop → dataset → placeholder)
- `GET /api/stream/mjpeg` - MJPEG stream endpoint - stream video mượt hơn, liên tục (phù hợp cho browser/WebView)
- `GET /api/stream/analyze` - Trả về kết quả phân tích realtime (JSON) cho frame camera mới nhất

## Ghi Chú

- Model/template cần được train trước khi sử dụng inference
- Cần ít nhất 3 ảnh chuẩn trong dataset để bắt đầu training (chỉ cần ảnh “đủ linh kiện”)
- Các file ảnh được lưu trong thư mục `data/` (tự động tạo). Sau mỗi lần train thành công, dataset sẽ được tự động xóa để đảm bảo mỗi lần train chỉ dành cho một mạch PCB.
- Video stream sẽ tự động:
  1. **Ưu tiên 1**: Stream từ camera laptop (nếu có)
  2. **Ưu tiên 2**: Hiển thị ảnh mới nhất từ dataset
  3. **Fallback**: Hiển thị placeholder nếu không có camera và dataset

- **Stream endpoints:**
  - `/api/stream/frame`: Lấy frame đơn lẻ (dùng cho polling) - Flutter app đang dùng với interval 100ms (~10 FPS)
  - `/api/stream/mjpeg`: MJPEG stream liên tục (~30 FPS) - phù hợp cho browser, WebView, hoặc các client hỗ trợ MJPEG
  
- Để thay đổi camera (nếu có nhiều camera), set environment variable: `CAMERA_INDEX=1` (mặc định là 0)

- **Lưu ý về lỗi upload dataset**: Đã sửa lỗi datetime serialization. Nếu gặp lỗi khi upload ảnh, đảm bảo backend đã được restart sau khi cập nhật code.

