#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// ---------------- Pin Mapping ----------------
constexpr uint8_t SENSOR_CAM = A3;
constexpr uint8_t SENSOR_REJ = A2;
constexpr uint8_t EMERGENCY_STOP = A1;
constexpr uint8_t CONVEYOR_PIN = 11;
constexpr uint8_t SERVO_PIN = 10;

// ---------------- Cấu hình Servo Gạt Ngược ----------------
constexpr uint8_t SERVO_REST_ANGLE = 180; 
constexpr uint8_t SERVO_PUSH_ANGLE = 0;   
constexpr uint16_t SERVO_SWEEP_DURATION = 1000; 

const int TRIGGER_LEVEL = LOW;

// --- Cấu hình Tốc độ Băng tải ---
constexpr uint8_t CONVEYOR_SPEED = 255; 

// ---------------- Trạng thái hệ thống ----------------
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo rejectServo;

bool waitingForResult = false;
bool pendingReject = false;      
bool conveyorRunning = true;
bool boardPassedCamera = false;
bool emergencyStopActive = false;  // Trạng thái dừng khẩn cấp (toggle)
bool lastEmergencyState = HIGH;    // Để detect edge khi nhấn nút
unsigned long lastHeartbeat = 0;
unsigned long cooldownTimer = 0; 
const unsigned long COOLDOWN_DELAY = 5000;
uint32_t okCount = 0;
uint32_t ngCount = 0;

// ---------------- Các hàm hỗ trợ ----------------

void sendEvent(String event) { Serial.println("EVENT:" + event); }

void setConveyor(bool run) {
  conveyorRunning = run;
  if (run) {
    analogWrite(CONVEYOR_PIN, 0);
  } else {
    analogWrite(CONVEYOR_PIN, 255);
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

// Hàm delay đơn giản (emergency stop đã được xử lý ở loop chính)
void safeDelay(unsigned long ms) {
  delay(ms);
}

void applyResult(bool isOk) {
  if (!waitingForResult) return;
  waitingForResult = false;
  boardPassedCamera = true;
  cooldownTimer = millis();

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
  
  // Chỉ resume băng tải nếu KHÔNG trong trạng thái emergency stop
  if (!emergencyStopActive) {
    setConveyor(true);
  }
}

void processCommand(String line) {
  line.trim();
  if (line == "CMD:RESULT:OK") applyResult(true);
  else if (line == "CMD:RESULT:NG") applyResult(false);
  else if (line == "CMD:START") {
    emergencyStopActive = false; // Clear emergency khi nhận lệnh START
    setConveyor(true);
  }
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
  setConveyor(true);
}

void loop() {
  // 1. Đọc lệnh từ Serial
  if (Serial.available()) {
    processCommand(Serial.readStringUntil('\n'));
  }

  // 2. Xử lý Nút dừng khẩn cấp (Toggle mode - bấm lần 1 dừng, lần 2 chạy)
  bool currentEmergencyState = digitalRead(EMERGENCY_STOP);
  if (lastEmergencyState == HIGH && currentEmergencyState == LOW) {
    // Phát hiện nhấn nút (falling edge)
    delay(50); // Debounce
    
    if (digitalRead(EMERGENCY_STOP) == LOW) { // Xác nhận vẫn còn nhấn
      emergencyStopActive = !emergencyStopActive; // Toggle trạng thái
      
      if (emergencyStopActive) {
        setConveyor(false);
        sendEvent("EMERGENCY_STOP");
        lcd.setCursor(0, 0);
        lcd.print("  DUNG KHAN!  ");
        lcd.setCursor(0, 1);
        lcd.print("Bam de chay lai");
      } else {
        setConveyor(true);
        sendEvent("EMERGENCY_RESUME");
        updateLcd(); // Khôi phục hiển thị bình thường
      }
    }
  }
  lastEmergencyState = currentEmergencyState;

  // 3. Xử lý Sensor Camera (chỉ hoạt động khi KHÔNG emergency stop)
  if (!emergencyStopActive) {
    bool cameraSensorActive = isSensorTriggered(SENSOR_CAM);
    if (!waitingForResult && !boardPassedCamera && conveyorRunning && cameraSensorActive) {
      setConveyor(false); 
      waitingForResult = true;
      sendEvent("BOARD_AT_CAMERA");
    }
    
    if (boardPassedCamera && cooldownTimer > 0 && (millis() - cooldownTimer >= COOLDOWN_DELAY)) {
      boardPassedCamera = false;
      cooldownTimer = 0;
      sendEvent("READY_FOR_NEXT");
    }
  }

  // 4. Xử lý Sensor Gạt (chỉ hoạt động khi KHÔNG emergency stop)
  if (!emergencyStopActive && isSensorTriggered(SENSOR_REJ)) {
    sendEvent("BOARD_AT_REJECT");
    
    if (pendingReject) {
      // Băng tải vẫn chạy trong lúc gạt
      
      // Bước 1: Gạt ngược
      rejectServo.write(SERVO_PUSH_ANGLE); 
      safeDelay(SERVO_SWEEP_DURATION);
      
      // Bước 2: Quay về
      rejectServo.write(SERVO_REST_ANGLE);
      safeDelay(SERVO_SWEEP_DURATION);
      
      pendingReject = false; 
      sendEvent("REJECT_DONE");
    }
    
    while(digitalRead(SENSOR_REJ) == TRIGGER_LEVEL); 
  }

  // 5. Gửi trạng thái
  if (millis() - lastHeartbeat >= 2000) {
    lastHeartbeat = millis();
    Serial.print("STATUS:OK="); Serial.print(okCount);
    Serial.print(",NG="); Serial.print(ngCount);
    Serial.print(" | CAM:"); Serial.print(digitalRead(SENSOR_CAM));
    Serial.print(" REJ:"); Serial.print(digitalRead(SENSOR_REJ));
    Serial.print(" | EMERGENCY:"); Serial.println(emergencyStopActive ? "ACTIVE" : "NORMAL");
  }
}