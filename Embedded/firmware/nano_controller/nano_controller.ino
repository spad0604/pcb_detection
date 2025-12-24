#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// ---------------- Pin Mapping ----------------
constexpr uint8_t SENSOR_CAM = A3;
constexpr uint8_t SENSOR_REJ = A2;
constexpr uint8_t EMERGENCY_STOP = A0;
constexpr uint8_t CONVEYOR_PIN = 11;
constexpr uint8_t SERVO_PIN = 10;

// ---------------- Cấu hình Servo & Tốc độ ----------------
constexpr uint8_t SERVO_REST_ANGLE = 20;
constexpr uint8_t SERVO_PUSH_ANGLE = 110;
constexpr uint16_t SERVO_PUSH_DURATION = 600;
const int TRIGGER_LEVEL = LOW;

// --- CẤU HÌNH TỐC ĐỘ BĂNG TẢI (0 - 255) ---
// 255 = Chạy nhanh nhất
// 150 = Chạy trung bình
// 80 - 100 = Chạy chậm (Nếu thấp quá motor sẽ không quay nổi)
constexpr uint8_t CONVEYOR_SPEED = 100; // <--- CHỈNH SỐ NÀY ĐỂ TĂNG/GIẢM TỐC

// ---------------- Trạng thái hệ thống ----------------
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo rejectServo;

bool waitingForResult = false;
bool pendingReject = false;
bool conveyorRunning = true;
bool boardPassedCamera = false;  // Để tránh detect lại board cũ
unsigned long lastHeartbeat = 0;
unsigned long cooldownTimer = 0;  // Timer để đợi 5s sau khi xử lý xong
const unsigned long COOLDOWN_DELAY = 5000;  // 5 giây cooldown
uint32_t okCount = 0;
uint32_t ngCount = 0;

// ---------------- Các hàm hỗ trợ ----------------

void sendEvent(String event) { Serial.println("EVENT:" + event); }

// SỬA HÀM NÀY: Dùng analogWrite thay vì digitalWrite
void setConveyor(bool run) {
  conveyorRunning = run;
  if (run) {
    analogWrite(CONVEYOR_PIN, CONVEYOR_SPEED); // Chạy với tốc độ đã cài
  } else {
    analogWrite(CONVEYOR_PIN, 0); // Dừng hẳn
  }
}

void updateLcd() {
  lcd.setCursor(0, 0); lcd.print("OK: "); lcd.print(okCount); lcd.print("      ");
  lcd.setCursor(0, 1); lcd.print("NG: "); lcd.print(ngCount); lcd.print("      ");
}

bool isSensorTriggered(int pin) {
  if (digitalRead(pin) == TRIGGER_LEVEL) {
    delay(50);
    if (digitalRead(pin) == TRIGGER_LEVEL) return true;
  }
  return false;
}

void applyResult(bool isOk) {
  if (!waitingForResult) return;
  waitingForResult = false;
  boardPassedCamera = true;  // Đánh dấu board này đã qua
  cooldownTimer = millis();  // Bắt đầu đếm 5s

  if (isOk) {
    okCount++;
    pendingReject = false;
    sendEvent("RESUME_OK");
  } else {
    ngCount++;
    pendingReject = true;
    sendEvent("RESUME_NG");
  }
  updateLcd();
  setConveyor(true);  // Chạy tiếp ngay, không cần đợi sensor nhả
}

void processCommand(String line) {
  line.trim();
  if (line == "CMD:RESULT:OK") applyResult(true);
  else if (line == "CMD:RESULT:NG") applyResult(false);
  else if (line == "CMD:START") setConveyor(true);
  else if (line == "CMD:STOP") setConveyor(false);
  else if (line == "CMD:RESET") {
    okCount = 0; ngCount = 0; updateLcd();
    sendEvent("RESET_DONE");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_CAM, INPUT_PULLUP);
  pinMode(SENSOR_REJ, INPUT_PULLUP);
  pinMode(EMERGENCY_STOP, INPUT_PULLUP);
  pinMode(CONVEYOR_PIN, OUTPUT);

  rejectServo.attach(SERVO_PIN);
  rejectServo.write(SERVO_REST_ANGLE);

  lcd.init();
  lcd.backlight();
  updateLcd();

  sendEvent("BOOT_SUCCESS");
  setConveyor(true); // Bắt đầu chạy chậm
}

void loop() {
  if (Serial.available()) {
    processCommand(Serial.readStringUntil('\n'));
  }

  // Kiểm tra sensor camera
  bool cameraSensorActive = isSensorTriggered(SENSOR_CAM);
  
  // Nếu board mới đến camera (chưa detect và chưa qua)
  if (!waitingForResult && !boardPassedCamera && conveyorRunning && cameraSensorActive) {
    setConveyor(false);  // Dừng để chụp ảnh rõ
    waitingForResult = true;
    sendEvent("BOARD_AT_CAMERA");
    // Đợi backend trả kết quả, khi có kết quả sẽ chạy tiếp ngay
  }
  
  // Reset flag sau 5 giây (để mạch kịp qua sensor)
  if (boardPassedCamera && cooldownTimer > 0 && (millis() - cooldownTimer >= COOLDOWN_DELAY)) {
    boardPassedCamera = false;
    cooldownTimer = 0;
    sendEvent("READY_FOR_NEXT");
  }

  if (isSensorTriggered(SENSOR_REJ)) {
    sendEvent("BOARD_AT_REJECT");
    if (pendingReject) {
      setConveyor(false);
      rejectServo.write(SERVO_PUSH_ANGLE);
      delay(SERVO_PUSH_DURATION);
      rejectServo.write(SERVO_REST_ANGLE);
      delay(400);
      pendingReject = false;
      setConveyor(true);
      sendEvent("REJECT_DONE");
    }
    while(digitalRead(SENSOR_REJ) == TRIGGER_LEVEL); 
  }

  if (digitalRead(EMERGENCY_STOP) == LOW && conveyorRunning) {
    setConveyor(false);
    sendEvent("EMERGENCY_STOP");
  }

  if (millis() - lastHeartbeat >= 2000) {
    lastHeartbeat = millis();
    Serial.print("STATUS:OK="); Serial.print(okCount);
    Serial.print(",NG="); Serial.print(ngCount);
    Serial.print(" | CAM:"); Serial.print(digitalRead(SENSOR_CAM));
    Serial.print(" REJ:"); Serial.println(digitalRead(SENSOR_REJ));
  }
}