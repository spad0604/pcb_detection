#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// ---------------- Pin Mapping ----------------
constexpr uint8_t SENSOR_CAM = A3;
constexpr uint8_t SENSOR_REJ = A2;
constexpr uint8_t EMERGENCY_STOP = A1;
constexpr uint8_t CONVEYOR_PIN = 11;
constexpr uint8_t SERVO_PIN = 10;

// ---------------- Cấu hình Servo ----------------
constexpr uint8_t SERVO_REST_ANGLE = 180; 
constexpr uint8_t SERVO_PUSH_ANGLE = 0;   
constexpr uint16_t SERVO_SWEEP_DURATION = 1000; 

const int TRIGGER_LEVEL = LOW;

// --- Cấu hình Thời gian ---
constexpr uint8_t CONVEYOR_SPEED = 255; 
const unsigned long CAMERA_STOP_DELAY = 250; // <--- THÊM: Thời gian trễ 300ms

// ---------------- Trạng thái Servo (State Machine) ----------------
enum ServoState {
  SERVO_IDLE,     
  SERVO_PUSHING,  
  SERVO_RETURNING 
};
ServoState currentServoState = SERVO_IDLE;
unsigned long servoTimer = 0;

// ---------------- Trạng thái hệ thống ----------------
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo rejectServo;

bool waitingForResult = false;
bool pendingReject = false;      
bool conveyorRunning = true;
bool boardPassedCamera = false;

// --- THÊM: Biến quản lý việc dừng trễ ---
bool stoppingForCamera = false;       // Cờ báo hiệu đang đếm lùi để dừng
unsigned long cameraStopTimer = 0;    // Timer đếm lùi

// Emergency Stop
bool emergencyStopActive = false;  
bool lastEmergencyState = HIGH;    
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
    analogWrite(CONVEYOR_PIN, 0); // Kích mức thấp
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
    unsigned long start = millis();
    while (millis() - start < 20); // Debounce 20ms
    if (digitalRead(pin) == TRIGGER_LEVEL) return true;
  }
  return false;
}

void applyResult(bool isOk) {
  if (emergencyStopActive) return;

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
  
  if (!emergencyStopActive) {
    setConveyor(true);
  }
}

void processCommand(String line) {
  line.trim();
  if (line == "CMD:RESULT:OK") applyResult(true);
  else if (line == "CMD:RESULT:NG") applyResult(false);
  else if (line == "CMD:START") {
    if (emergencyStopActive) {
       emergencyStopActive = false; 
    }
    setConveyor(true);
  }
  else if (line == "CMD:STOP") setConveyor(false);
  else if (line == "CMD:RESET") {
    okCount = 0; ngCount = 0; updateLcd();
    stoppingForCamera = false; // Reset cờ dừng trễ
    sendEvent("RESET_DONE");
  }
}

void handleServoLogic() {
  if (emergencyStopActive) {
    if (currentServoState != SERVO_IDLE) {
      rejectServo.write(SERVO_REST_ANGLE);
      currentServoState = SERVO_IDLE;
    }
    return;
  }

  switch (currentServoState) {
    case SERVO_IDLE:
      if (pendingReject && isSensorTriggered(SENSOR_REJ)) {
        sendEvent("BOARD_AT_REJECT");
        rejectServo.write(SERVO_PUSH_ANGLE);
        servoTimer = millis();              
        currentServoState = SERVO_PUSHING;   
      }
      break;

    case SERVO_PUSHING:
      if (millis() - servoTimer >= SERVO_SWEEP_DURATION) {
        rejectServo.write(SERVO_REST_ANGLE);
        servoTimer = millis();              
        currentServoState = SERVO_RETURNING; 
      }
      break;

    case SERVO_RETURNING:
      if (millis() - servoTimer >= SERVO_SWEEP_DURATION) {
        pendingReject = false;
        currentServoState = SERVO_IDLE;      
        sendEvent("REJECT_DONE");
      }
      break;
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
  // 1. Đọc lệnh Serial
  if (Serial.available()) {
    processCommand(Serial.readStringUntil('\n'));
  }

  // 2. Xử lý Nút dừng khẩn cấp
  bool currentEmergencyState = digitalRead(EMERGENCY_STOP);
  if (lastEmergencyState == HIGH && currentEmergencyState == LOW) {
    unsigned long dbStart = millis();
    while(millis() - dbStart < 50); 
    
    if (digitalRead(EMERGENCY_STOP) == LOW) { 
      emergencyStopActive = !emergencyStopActive; 
      
      if (emergencyStopActive) {
        setConveyor(false);
        stoppingForCamera = false; // Hủy bỏ quá trình đếm ngược nếu có
        sendEvent("EMERGENCY_STOP");
        lcd.setCursor(0, 0); lcd.print("  DUNG KHAN!  ");
        lcd.setCursor(0, 1); lcd.print("Bam de chay lai");
        
        rejectServo.write(SERVO_REST_ANGLE);
        currentServoState = SERVO_IDLE;

      } else {
        setConveyor(true);
        sendEvent("EMERGENCY_RESUME");
        updateLcd(); 
      }
    }
  }
  lastEmergencyState = currentEmergencyState;

  // 3. Xử lý Servo
  handleServoLogic();

  // 4. Xử lý Sensor Camera (Logic MỚI)
  if (!emergencyStopActive) {
    
    // Đọc cảm biến
    bool cameraSensorActive = isSensorTriggered(SENSOR_CAM);

    // [A] Phát hiện vật lần đầu -> Bắt đầu đếm ngược 300ms
    if (!waitingForResult && !boardPassedCamera && !stoppingForCamera && conveyorRunning && cameraSensorActive) {
      stoppingForCamera = true;
      cameraStopTimer = millis();
      // LƯU Ý: Không setConveyor(false) ở đây, để nó chạy tiếp
    }

    // [B] Đã đếm đủ 300ms -> Dừng băng tải và gọi Camera chụp
    if (stoppingForCamera && (millis() - cameraStopTimer >= CAMERA_STOP_DELAY)) {
      setConveyor(false);       // Dừng băng tải
      stoppingForCamera = false; // Reset cờ đếm
      waitingForResult = true;   // Chuyển sang trạng thái đợi Python
      sendEvent("BOARD_AT_CAMERA");
    }
    
    // [C] Logic Cool-down sau khi xong (tránh chụp lặp lại vật cũ)
    if (boardPassedCamera && cooldownTimer > 0 && (millis() - cooldownTimer >= COOLDOWN_DELAY)) {
      boardPassedCamera = false;
      cooldownTimer = 0;
      sendEvent("READY_FOR_NEXT");
    }
  }

  // 5. Gửi Heartbeat
  if (millis() - lastHeartbeat >= 2000) {
    lastHeartbeat = millis();
    Serial.print("STATUS:OK="); Serial.print(okCount);
    Serial.print(",NG="); Serial.print(ngCount);
    Serial.print(" | CAM:"); Serial.print(digitalRead(SENSOR_CAM));
    Serial.print(" REJ:"); Serial.print(digitalRead(SENSOR_REJ));
    Serial.print(" | EMERGENCY:"); Serial.println(emergencyStopActive ? "ACTIVE" : "NORMAL");
  }
}