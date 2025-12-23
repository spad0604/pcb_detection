#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// ---------------- Pin mapping (Đã cập nhật) ----------------
constexpr uint8_t SENSOR_CAMERA_PIN = A2;   // Cảm biến tại vị trí Camera
constexpr uint8_t SENSOR_REJECT_PIN = A3;   // Cảm biến tại vị trí Servo (A3)
constexpr uint8_t EMERGENCY_STOP_PIN = A0;  // Nút dừng khẩn cấp
constexpr uint8_t CONVEYOR_PIN = 11;        // Điều khiển băng tải
constexpr uint8_t SERVO_PIN = 10;           // Điều khiển Servo

// ---------------- Servo config ----------------
constexpr uint8_t SERVO_REST_ANGLE = 20;
constexpr uint8_t SERVO_PUSH_ANGLE = 110;
constexpr uint16_t SERVO_PUSH_DURATION = 600; 

// ---------------- Serial protocol ----------------
constexpr unsigned long SERIAL_BAUD = 115200;
constexpr unsigned long HEARTBEAT_INTERVAL = 2000; 

LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo rejectServo;

// ---------------- Runtime state ----------------
bool waitingForResult = false;
bool pendingReject = false;
bool conveyorRunning = true;
bool servoEngaged = false;
unsigned long servoActionStart = 0;
unsigned long lastHeartbeat = 0;

uint32_t okCount = 0;
uint32_t ngCount = 0;

// Trạng thái để kiểm tra sườn xuống (chống lặp tín hiệu)
bool lastCameraLevel = HIGH;
bool lastRejectLevel = HIGH;

void sendEvent(const String &payload) {
  Serial.println(payload);
}

void setConveyor(bool run) {
  conveyorRunning = run;
  digitalWrite(CONVEYOR_PIN, run ? HIGH : LOW);
}

void updateLcd() {
  lcd.setCursor(0, 0);
  lcd.print("OK:");
  lcd.print(okCount);
  lcd.print("      ");
  lcd.setCursor(0, 1);
  lcd.print("NG:");
  lcd.print(ngCount);
  lcd.print("      ");
}

void engageServo() {
  servoEngaged = true;
  servoActionStart = millis();
  rejectServo.write(SERVO_PUSH_ANGLE);
  sendEvent("EVENT:SERVO_PUSH"); // Gửi về server
}

void releaseServoIfDue() {
  if (servoEngaged && millis() - servoActionStart >= SERVO_PUSH_DURATION) {
    rejectServo.write(SERVO_REST_ANGLE);
    servoEngaged = false;
    pendingReject = false;
    setConveyor(true);
    sendEvent("EVENT:REJECT_DONE");
  }
}

// Xử lý cảm biến A2 (Camera)
void handleCameraSensor(bool currentLevel) {
  // Nếu phát hiện vật (LOW) và trước đó là HIGH (chưa có vật)
  if (currentLevel == LOW && lastCameraLevel == HIGH && !waitingForResult && conveyorRunning) {
    setConveyor(false); // Dừng băng tải để chụp ảnh
    waitingForResult = true;
    sendEvent("EVENT:BOARD_AT_CAMERA"); // Báo server chụp ảnh
  }
  lastCameraLevel = currentLevel;
}

// Xử lý cảm biến A3 (Reject)
void handleRejectSensor(bool currentLevel) {
  // Khi cảm biến A3 thấy vật (LOW)
  if (currentLevel == LOW && lastRejectLevel == HIGH) {
    sendEvent("EVENT:BOARD_AT_REJECT"); // Gửi lệnh báo cho server vật đã đến A3
    
    // Nếu vật này đã được server xác định là NG (pendingReject)
    if (pendingReject && !servoEngaged) {
      setConveyor(false);
      engageServo();
    }
  }
  lastRejectLevel = currentLevel;
}

void applyResult(bool isOk) {
  if (!waitingForResult) {
    sendEvent("ERROR:UNEXPECTED_RESULT");
    return;
  }
  waitingForResult = false;

  if (isOk) {
    okCount++;
    pendingReject = false;
  } else {
    ngCount++;
    pendingReject = true; // Đánh dấu vật này cần bị gạt
  }
  updateLcd();
  setConveyor(true);
  sendEvent("EVENT:RESUME");
}

void processCommand(const String &line) {
  if (line == "CMD:RESULT:OK") applyResult(true);
  else if (line == "CMD:RESULT:NG") applyResult(false);
  else if (line == "CMD:START") setConveyor(true);
  else if (line == "CMD:STOP") setConveyor(false);
  else if (line == "CMD:RESET") {
      okCount = 0; ngCount = 0; updateLcd();
      sendEvent("EVENT:RESET_DONE");
  }
}

void setup() {
  // Dùng INPUT_PULLUP để đảm bảo ổn định khi không có vật
  pinMode(SENSOR_CAMERA_PIN, INPUT_PULLUP);
  pinMode(SENSOR_REJECT_PIN, INPUT_PULLUP);
  pinMode(EMERGENCY_STOP_PIN, INPUT_PULLUP);
  pinMode(CONVEYOR_PIN, OUTPUT);

  rejectServo.attach(SERVO_PIN);
  rejectServo.write(SERVO_REST_ANGLE);

  lcd.init();
  lcd.backlight();
  updateLcd();

  Serial.begin(SERIAL_BAUD);
  sendEvent("EVENT:BOOT");
  setConveyor(true);
}

void loop() {
  // 1. Đọc lệnh từ Server
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    processCommand(line);
  }

  // 2. Kiểm tra cảm biến với logic LOW = Có vật
  handleCameraSensor(digitalRead(SENSOR_CAMERA_PIN));
  handleRejectSensor(digitalRead(SENSOR_REJECT_PIN));

  // 3. Quản lý Servo và Dừng khẩn cấp
  releaseServoIfDue();

  if (digitalRead(EMERGENCY_STOP_PIN) == LOW && conveyorRunning) {
    setConveyor(false);
    sendEvent("EVENT:EMERGENCY_STOP");
  }

  // 4. Heartbeat để server biết Arduino vẫn sống
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = millis();
    // Gửi kèm trạng thái hiện tại
    Serial.println("STATUS:OK=" + String(okCount) + ",NG=" + String(ngCount));
  }
}