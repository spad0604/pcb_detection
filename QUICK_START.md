# 🚀 Quick Start - PCB Detection

## Chạy nhanh trong 3 bước:

### 1️⃣ Chạy Backend (Terminal 1)
```bash
cd Embedded/backend
./start_server.sh
```
Hoặc chạy thủ công:
```bash
cd Embedded/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2️⃣ Chạy Frontend (Terminal 2 - mở terminal mới)
```bash
cd Desktop
./start_app.sh
```
Hoặc chạy thủ công:
```bash
cd Desktop
flutter pub get
flutter run -d linux  # hoặc windows/macos tùy hệ điều hành
```

### 3️⃣ Sử dụng
- Mở ứng dụng Flutter đã chạy
- Upload ảnh PCB *đủ linh kiện* (cùng một mạch, nhiều góc càng tốt)
- Nhập tên mạch PCB và train (mỗi lần train cho một mạch riêng, không cần ảnh lỗi)
- Sau khi train thành công, dataset sẽ tự động được làm trống để chuẩn bị cho mạch tiếp theo
- Mở panel Live feed để xem hệ thống tự phát hiện linh kiện thiếu theo thời gian thực

---

**Chi tiết đầy đủ:** Xem file `HUONG_DAN_CHAY.md`

