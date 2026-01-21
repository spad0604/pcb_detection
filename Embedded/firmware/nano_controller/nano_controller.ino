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
const unsigned long CAMERA_STOP_DELAY = 250; // Trễ để vật nằm giữa camera

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
bool conveyorRunning = true;
bool boardPassedCamera = false;

bool stoppingForCamera = false;       
unsigned long cameraStopTimer = 0;    

// Emergency Stop
bool emergencyStopActive = false;  
bool lastEmergencyState = HIGH;    
unsigned long lastHeartbeat = 0;
unsigned long cooldownTimer = 0; 
const unsigned long COOLDOWN_DELAY = 5000;

uint32_t okCount = 0;
uint32_t ngCount = 0;

// ---------------- Hàng đợi kết quả (FIFO) ----------------
// Lý do: nếu có nhiều mạch chạy liên tiếp, kết quả OK/NG cần được giữ theo thứ tự
// và sẽ được "consume" khi mạch đi tới cảm biến gạt (SENSOR_REJ).
constexpr uint8_t RESULT_QUEUE_SIZE = 8;
bool resultQueue[RESULT_QUEUE_SIZE]; // true = NG (cần gạt), false = OK (không gạt)
uint8_t resultHead = 0;
uint8_t resultTail = 0;
uint8_t resultCount = 0;

bool enqueueResult(bool shouldReject) {
  if (resultCount >= RESULT_QUEUE_SIZE) {
    // Overflow hiếm khi xảy ra; log event để debug.
    // Chọn drop oldest để hệ thống tiếp tục chạy.
    resultHead = (resultHead + 1) % RESULT_QUEUE_SIZE;
    resultCount--;
    sendEvent("QUEUE_OVERFLOW_DROP_OLDEST");
  }
  resultQueue[resultTail] = shouldReject;
  resultTail = (resultTail + 1) % RESULT_QUEUE_SIZE;
  resultCount++;
  return true;
}

bool dequeueResult(bool &shouldReject) {
  if (resultCount == 0) return false;
  shouldReject = resultQueue[resultHead];
  resultHead = (resultHead + 1) % RESULT_QUEUE_SIZE;
  resultCount--;
  return true;
}

// ---------------- Các hàm hỗ trợ ----------------

void sendEvent(String event) { Serial.println("EVENT:" + event); }

// Cập nhật màn hình LCD
void updateLcd() {
  lcd.setCursor(0, 0); 
  lcd.print("OK: "); lcd.print(okCount);
  lcd.print("                "); // Xóa ký tự thừa
  lcd.setCursor(0, 1); 
  lcd.print("NG: "); lcd.print(ngCount);
  lcd.print("                "); // Xóa ký tự thừa
}

void setConveyor(bool run) {
  conveyorRunning = run;
  if (run) {
    analogWrite(CONVEYOR_PIN, 0); // Kích mức thấp (tùy relay)
  } else {
    analogWrite(CONVEYOR_PIN, 255);
  }
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
    enqueueResult(false);
    sendEvent("RESUME_OK");
  } else {
    ngCount++;
    enqueueResult(true);
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
    if (emergencyStopActive) emergencyStopActive = false; 
    setConveyor(true);
  }
  else if (line == "CMD:STOP") setConveyor(false);
  else if (line == "CMD:RESET") {
    okCount = 0; ngCount = 0; 
    lcd.clear();
    updateLcd();
    stoppingForCamera = false;
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
      if (isSensorTriggered(SENSOR_REJ)) {
        sendEvent("BOARD_AT_REJECT");

        bool shouldReject = false;
        bool hasDecision = dequeueResult(shouldReject);
        if (!hasDecision) {
          // Có board tới reject nhưng chưa có kết quả tương ứng (mismatch timing).
          // Mặc định không gạt để tránh gạt nhầm.
          sendEvent("REJECT_NO_DECISION");
          break;
        }

        if (shouldReject) {
          rejectServo.write(SERVO_PUSH_ANGLE);
          servoTimer = millis();
          currentServoState = SERVO_PUSHING;
        } else {
          sendEvent("PASS_OK");
        }
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
        currentServoState = SERVO_IDLE;      
        sendEvent("REJECT_DONE");
      }
      break;
  }
}

// ---------------- Setup & Loop ----------------

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
  // 1. Nhận lệnh từ Serial
  if (Serial.available()) {
    processCommand(Serial.readStringUntil('\n'));
  }

  // 2. Xử lý Dừng khẩn cấp (Emergency Stop)
  bool currentEmergencyState = digitalRead(EMERGENCY_STOP);
  if (lastEmergencyState == HIGH && currentEmergencyState == LOW) {
    delay(50); // Debounce nhanh
    if (digitalRead(EMERGENCY_STOP) == LOW) { 
      emergencyStopActive = !emergencyStopActive; 
      
      lcd.clear(); // XÓA MÀN HÌNH MỖI KHI THAY ĐỔI TRẠNG THÁI

      if (emergencyStopActive) {
        setConveyor(false);
        stoppingForCamera = false; 
        sendEvent("EMERGENCY_STOP");
        
        lcd.setCursor(0, 0); lcd.print("  DUNG KHAN!  ");
        lcd.setCursor(0, 1); lcd.print("Bam de chay lai");
        
        rejectServo.write(SERVO_REST_ANGLE);
        currentServoState = SERVO_IDLE;
      } else {
        // TRẠNG THÁI BÌNH THƯỜNG TRỞ LẠI
        setConveyor(true);
        sendEvent("EMERGENCY_RESUME");
        updateLcd(); // Vẽ lại OK/NG sau khi đã lcd.clear()
      }
    }
  }
  lastEmergencyState = currentEmergencyState;

  // 3. Xử lý Servo (nếu không dừng khẩn)
  handleServoLogic();

  // 4. Xử lý Cảm biến Camera
  if (!emergencyStopActive) {
    bool cameraSensorActive = isSensorTriggered(SENSOR_CAM);

    // Phát hiện vật: Bắt đầu đếm trễ để dừng đúng tâm
    if (!waitingForResult && !boardPassedCamera && !stoppingForCamera && conveyorRunning && cameraSensorActive) {
      stoppingForCamera = true;
      cameraStopTimer = millis();
    }

    // Khi đủ thời gian trễ: Dừng băng tải và báo cho Python chụp ảnh
    if (stoppingForCamera && (millis() - cameraStopTimer >= CAMERA_STOP_DELAY)) {
      setConveyor(false);       
      stoppingForCamera = false; 
      waitingForResult = true;   
      sendEvent("BOARD_AT_CAMERA");
    }
    
    // Cooldown để tránh cảm biến bị kích hoạt liên tục bởi cùng 1 vật
    if (boardPassedCamera && cooldownTimer > 0 && (millis() - cooldownTimer >= COOLDOWN_DELAY)) {
      boardPassedCamera = false;
      cooldownTimer = 0;
      sendEvent("READY_FOR_NEXT");
    }
  }

  // 5. Gửi Status định kỳ (Heartbeat)
  if (millis() - lastHeartbeat >= 2000) {
    lastHeartbeat = millis();
    Serial.print("STATUS:OK="); Serial.print(okCount);
    Serial.print(",NG="); Serial.print(ngCount);
    Serial.print(" | EMERGENCY:"); Serial.println(emergencyStopActive ? "ACTIVE" : "NORMAL");
  }
}