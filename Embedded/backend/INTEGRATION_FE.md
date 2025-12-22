# Tích hợp Frontend với Line Controller

## Luồng hoạt động

```
Arduino phát hiện mạch 
  → Gửi EVENT:BOARD_AT_CAMERA 
  → Backend chụp ảnh + chạy YOLO inference
  → Lưu kết quả vào LineController.last_result
  → Gửi CMD:RESULT:OK/NG về Arduino
  → Frontend poll API để hiển thị kết quả real-time
```

## API Endpoints cho Frontend

### 1. Lấy trạng thái băng tải (polling mỗi 1-2s)

**GET** `/api/line/status`

Response:
```json
{
  "port": "/dev/ttyUSB0",
  "baud": 115200,
  "connected": true,
  "okCount": 15,
  "ngCount": 3,
  "machineState": {
    "RUN": true,
    "WAIT": false,
    "REJECTPEND": false
  },
  "waitingForDetection": false,
  "lastInference": {
    "boardName": "LM2596",
    "isDefective": true,
    "confidence": 0.89,
    "totalComponents": 11,
    "detectedComponents": 9,
    "missingAreas": [
      {"name": "U1", "position": "center", "confidence": 0.0},
      {"name": "C2", "position": "top-left", "confidence": 0.0}
    ],
    "message": "Phát hiện 2 vị trí thiếu linh kiện"
  },
  "lastStatusRaw": "STATUS:OK=15,NG=3,RUN=1,WAIT=0,REJECTPEND=0"
}
```

**Cách dùng:**
- Poll endpoint này mỗi 1-2 giây để cập nhật UI real-time
- Hiển thị `okCount` / `ngCount` trên dashboard
- Khi `lastInference` không null → hiển thị kết quả kiểm tra mới nhất
- `lastInference.missingAreas` → danh sách linh kiện thiếu (giống khi user upload ảnh)

### 2. Lấy kết quả inference mới nhất (khi cần chi tiết)

**GET** `/api/line/last_inference`

Response: giống 100% với `/api/inference` (upload ảnh)
```json
{
  "boardName": "LM2596",
  "isDefective": true,
  "confidence": 0.89,
  "totalComponents": 11,
  "detectedComponents": 9,
  "missingAreas": [
    {"name": "U1", "position": "center", "confidence": 0.0},
    {"name": "C2", "position": "top-left", "confidence": 0.0}
  ],
  "message": "Phát hiện 2 vị trí thiếu linh kiện"
}
```

**Cách dùng:**
- Gọi khi user click vào "Xem chi tiết inference cuối cùng"
- Hiển thị UI giống y hệt như upload ảnh (reuse component)

### 3. Gửi lệnh thủ công (testing/control)

**POST** `/api/line/command`

Request:
```json
{
  "command": "CMD:RESET"
}
```

Response:
```json
{
  "sent": "CMD:RESET"
}
```

**Các lệnh hỗ trợ:**
- `CMD:START` - Bật băng tải
- `CMD:STOP` - Dừng băng tải
- `CMD:RESET` - Reset counters (OK=0, NG=0)
- `CMD:STATUS?` - Yêu cầu Arduino gửi status ngay
- `CMD:SERVO:TEST` - Test servo reject

## Ví dụ code Flutter (GetX)

```dart
class LineStatusController extends GetxController {
  final Rx<LineStatus?> status = Rx(null);
  Timer? _pollTimer;

  @override
  void onInit() {
    super.onInit();
    startPolling();
  }

  void startPolling() {
    _pollTimer = Timer.periodic(Duration(seconds: 2), (_) async {
      try {
        final response = await http.get(Uri.parse('http://localhost:8000/api/line/status'));
        if (response.statusCode == 200) {
          status.value = LineStatus.fromJson(jsonDecode(response.body));
        }
      } catch (e) {
        print('Poll error: $e');
      }
    });
  }

  Future<void> sendCommand(String cmd) async {
    await http.post(
      Uri.parse('http://localhost:8000/api/line/command'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'command': cmd}),
    );
  }

  @override
  void onClose() {
    _pollTimer?.cancel();
    super.onClose();
  }
}
```

```dart
// Widget hiển thị kết quả real-time
Obx(() {
  final inference = controller.status.value?.lastInference;
  if (inference == null) return Text('Chờ mạch vào...');
  
  return Column(
    children: [
      Text('Mạch: ${inference.boardName}'),
      Text('Kết quả: ${inference.isDefective ? "THIẾU" : "ĐỦ"}'),
      Text('Độ tin cậy: ${(inference.confidence * 100).toStringAsFixed(1)}%'),
      if (inference.missingAreas.isNotEmpty) ...[
        Text('Thiếu ${inference.missingAreas.length} linh kiện:'),
        ...inference.missingAreas.map((area) => Text('- ${area.name} (${area.position})')),
      ],
    ],
  );
})
```

## Tóm tắt

1. **Polling `/api/line/status`** mỗi 1-2s → cập nhật OK/NG count + last inference
2. **`lastInference`** object có cấu trúc giống y hệt response của `/api/inference` → **reuse UI component**
3. Frontend không cần thay đổi logic hiển thị inference result, chỉ cần lấy từ polling thay vì upload file
4. Khi `lastInference` update → hiển thị ngay trên UI (real-time feedback)
