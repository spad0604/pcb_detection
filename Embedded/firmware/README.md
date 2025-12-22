# Firmware Overview

Mạch Arduino Nano sẽ làm nhiệm vụ điều khiển băng tải, hai cảm biến tiệm cận và servo gạt, đồng thời giao tiếp với backend thông qua Serial (USB). Mọi file nguồn được đặt trong cùng thư mục này để tách biệt khỏi backend.

## Phần cứng & Mapping chân

| Thành phần               | Chân Nano | Ghi chú |
|-------------------------|-----------|--------|
| Công tắc `SW`           | A0        | Nút STOP khẩn, Active LOW |
| Proximity sensor 2 (`IN2`) | A1     | Phát hiện bo trước cơ cấu gạt |
| Proximity sensor 1 (`IN1`) | A2     | Phát hiện bo tại vị trí camera |
| LCD 16x2 I2C            | SDA=A4 / SCL=A5 | Dùng module PCF8574 |
| Relay/MOSFET động cơ (`DC`) | D12   | `HIGH` chạy, `LOW` dừng |
| Servo loại SG90 (`SERVO`)  | D11    | Điều khiển gạt bo lỗi |
| UART USB                | D0 / D1  | Serial tới backend |

Các chân có thể sửa trong file `.ino` nếu cần.

## Giao thức Serial

- Baud rate: **115200**
- Mỗi gói lệnh là chuỗi ASCII kết thúc bằng `\n`.

### Lệnh từ Backend -> Nano

| Lệnh                  | Ý nghĩa |
|----------------------|--------|
| `CMD:RESULT:OK`      | Đã detect xong, bo đạt. Nano cộng bộ đếm OK và cho băng tải chạy tiếp |
| `CMD:RESULT:NG`      | Bo lỗi. Nano cộng bộ đếm NG, cho băng tải chạy tiếp và gạt bo ở cảm biến 2 |
| `CMD:START`          | Ép băng tải chạy |
| `CMD:STOP`           | Ép băng tải dừng |
| `CMD:RESET`          | Reset bộ đếm và trạng thái |
| `CMD:STATUS?`        | Yêu cầu Nano gửi lại số liệu hiện tại |
| `CMD:SERVO:TEST`     | Chạy thử chuyển động gạt |

### Sự kiện Nano -> Backend

| Event                             | Thời điểm |
|----------------------------------|-----------|
| `EVENT:BOOT`                     | Sau khi khởi động |
| `EVENT:BOARD_AT_CAMERA`          | Sensor 1 phát hiện bo -> băng tải dừng, yêu cầu detect |
| `EVENT:RESUME`                   | Đã nhận kết quả & cho băng tải chạy |
| `EVENT:REJECT_DONE`              | Servo đã gạt xong bo lỗi |
| `STATUS:OK=xx,NG=yy`             | Gửi định kỳ hoặc khi backend yêu cầu |
| `ERROR:<message>`                | Bất thường (ví dụ thiếu profile) |

## Chu trình hoạt động

1. Băng tải chạy mặc định.
2. Sensor 1 phát hiện bo tại vị trí camera -> Nano dừng băng tải và gửi `EVENT:BOARD_AT_CAMERA`.
3. Backend nhận hình ảnh, detect và trả `CMD:RESULT:OK` hoặc `CMD:RESULT:NG`.
4. Nano cập nhật LCD, cộng bộ đếm và cho băng tải tiếp tục.
5. Nếu bo lỗi, khi sensor 2 kích hoạt thì Nano dừng ngắn, quay servo gạt, sau đó cho chạy tiếp và gửi `EVENT:REJECT_DONE`.
6. Backend có thể gửi `CMD:STATUS?` hoặc `CMD:RESET` bất kỳ lúc nào.

Code mẫu chi tiết nằm trong `nano_controller/nano_controller.ino`.

## Tích hợp backend

- Biến môi trường:
  - `NANO_PORT`: tên cổng Serial (mặc định `/dev/ttyUSB0`).
  - `NANO_BAUD`: tốc độ giao tiếp (mặc định `115200`).
- Service `LineController` (`app/services/line_controller.py`) sẽ:
  1. Lắng nghe `EVENT:BOARD_AT_CAMERA`, chụp frame từ camera và chạy YOLO.
  2. Gửi `CMD:RESULT:{OK|NG}` trở lại Nano để cho băng tải chạy tiếp hoặc gạt bo lỗi.
  3. Đồng bộ bộ đếm OK/NG, trạng thái chờ và kết quả cuối cùng để FE hiển thị.

### REST API

- `GET /api/line/status`: trả về port Serial, trạng thái kết nối, số lượng OK/NG và kết quả auto-detect gần nhất.
- `POST /api/line/command` với payload `{ "command": "CMD:START" }`: gửi lệnh bất kỳ tới Nano (START/STOP/RESET/SERVO:TEST...).

Ví dụ reset bộ đếm:

```bash
curl -X POST http://127.0.0.1:8000/api/line/command \
  -H 'Content-Type: application/json' \
  -d '{"command":"CMD:RESET"}'
```

Sau khi bật backend, cắm Nano vào USB (đúng cổng `NANO_PORT`), toàn bộ chu trình cảm biến → detect → servo sẽ diễn ra tự động.
