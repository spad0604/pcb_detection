// ---------------- Pin Mapping ----------------
const int PIN_CONVEYOR = 11;      // Chân điều khiển Relay/Motor băng tải
const int PIN_SENSOR_1  = A2;     // Cảm biến 1 (Vị trí đầu)
const int PIN_SENSOR_2  = A3;     // Cảm biến 2 (Vị trí cuối)
const int PIN_BTN_START = 2;      // Nút nhấn Bắt đầu (Start)
const int PIN_BTN_STOP  = 3;      // Nút nhấn Dừng (Stop)
const int PIN_EMERGENCY = A0;     // Nút dừng khẩn cấp

// ---------------- Biến trạng thái ----------------
bool isRunning = false;           // Trạng thái băng tải đang chạy hay dừng

void setup() {
  Serial.begin(9600);

  // Cấu hình chân Output
  pinMode(PIN_CONVEYOR, OUTPUT);
  digitalWrite(PIN_CONVEYOR, LOW); // Mặc định dừng

  // Cấu hình chân Input với điện trở kéo lên nội trở (INPUT_PULLUP)
  // Khi nhấn nút hoặc cảm biến kích hoạt, giá trị sẽ là LOW
  pinMode(PIN_SENSOR_1, INPUT_PULLUP);
  pinMode(PIN_SENSOR_2, INPUT_PULLUP);
  pinMode(PIN_BTN_START, INPUT_PULLUP);
  pinMode(PIN_BTN_STOP, INPUT_PULLUP);
  pinMode(PIN_EMERGENCY, INPUT_PULLUP);

  Serial.println("He thong da san sang!");
}

void loop() {
  // 1. Đọc trạng thái nút nhấn & Cảm biến
  bool startState = digitalRead(PIN_BTN_START);
  bool stopState  = digitalRead(PIN_BTN_STOP);
  bool emergencyState = digitalRead(PIN_EMERGENCY);
  bool sensor1State = digitalRead(PIN_SENSOR_1);
  bool sensor2State = digitalRead(PIN_SENSOR_2);

  // 2. Logic điều khiển băng tải
  
  // Nhấn START -> Chạy
  if (startState == LOW) { 
    isRunning = true;
    Serial.println("Lenh: START");
    delay(200); // Chống dội nút nhấn
  }

  // Nhấn STOP hoặc Dừng khẩn cấp -> Dừng ngay
  if (stopState == LOW || emergencyState == LOW) {
    isRunning = false;
    Serial.println("Lenh: STOP / EMERGENCY");
    delay(200);
  }

  // 3. Xử lý cảm biến (Ví dụ: Ghi log khi thấy vật)
  if (sensor1State == LOW) {
    Serial.println("Sensor 1: Co vat!");
  }
  
  if (sensor2State == LOW) {
    Serial.println("Sensor 2: Co vat!");
    // Ví dụ: Tự động dừng khi vật đến cuối băng tải
    // isRunning = false; 
  }

  // 4. Xuất lệnh điều khiển ra chân vật lý
  if (isRunning) {
    digitalWrite(PIN_CONVEYOR, HIGH);
  } else {
    digitalWrite(PIN_CONVEYOR, LOW);
  }

  delay(50); // Nghỉ ngắn để hệ thống ổn định
}
