import os
from dotenv import load_dotenv

load_dotenv()

# --- Servo channels (PCA9685 channel index per joint) ---
# Mapped from hardware diagram:
#   Ch 00 = R1 = front_right_hip
#   Ch 01 = R2 = front_right_knee
#   Ch 02 = L1 = front_left_hip
#   Ch 03 = L2 = front_left_knee
#   Ch 04 = R4 = rear_right_knee
#   Ch 05 = R3 = rear_right_hip
#   Ch 06 = L3 = rear_left_hip
#   Ch 07 = L4 = rear_left_knee
SERVO_CHANNELS = {
    "front_right_hip":  0,
    "front_right_knee": 1,
    "front_left_hip":   2,
    "front_left_knee":  3,
    "rear_right_knee":  4,
    "rear_right_hip":   5,
    "rear_left_hip":    6,
    "rear_left_knee":   7,
}

# --- Servo angle limits (degrees) ---
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180

# --- Standing pose (degrees per joint) ---
# Vertical angles (straight down) per diagram — tune these after physical test
STAND_POSE = {
    "front_right_hip":  90,
    "front_right_knee": 90,
    "front_left_hip":   90,
    "front_left_knee":  135,
    "rear_right_knee":  90,
    "rear_right_hip":   90,
    "rear_left_hip":    90,
    "rear_left_knee":   90,
}

# --- Gait parameters ---
GAIT_STEP_ANGLE = 20    # degrees hip swings per step
GAIT_LIFT_ANGLE = 30    # degrees knee lifts per step
GAIT_STEP_DELAY = 0.15  # seconds between each phase

# --- PCA9685 ---
I2C_BUS         = 1
PCA9685_ADDRESS = 0x40
PWM_FREQUENCY   = 50    # Hz — standard for servos

# --- Development flags ---
# Set True to skip real I2C/servo hardware and print commands to the terminal instead.
MOCK_SERVOS = True

# --- Vision ---
CAMERA_RESOLUTION  = (640, 480)
DETECTION_MODEL    = "models/MobileNetSSD_deploy.caffemodel"
DETECTION_PROTOTXT = "models/MobileNetSSD_deploy.prototxt"
DETECTION_CONFIDENCE_THRESHOLD = 0.5

# --- LLM ---
OLLAMA_BASE_URL  = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL        = os.environ.get("CLEO_MODEL", "gemma4")
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY")   # optional — used as fallback if Ollama fails
GEMINI_MODEL     = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
VALID_ACTIONS    = [
    "walk_forward", "turn_left", "turn_right",
    "stop", "complete", "speak", "set_mode",
]

# --- Voice ---
WHISPER_MODEL    = "tiny.en"
TTS_LANGUAGE     = "en"
MIC_SAMPLE_RATE  = 16000
MIC_DEVICE_INDEX = None  # None = default USB mic

# --- OLED ---
OLED_WIDTH       = 128
OLED_HEIGHT      = 64
OLED_I2C_ADDRESS = 0x3C
OLED_DRIVER      = "sh1106"   # "sh1106" or "ssd1306" — check your display's chip

# --- Module bay ---
PIR_GPIO_PIN     = 17
DHT11_GPIO_PIN   = 27
MODULE_I2C_ADDRESSES = {
    0x44: "environment",  # DHT11 via I2C adapter
}

# --- Known robot modes ---
KNOWN_MODES = ["general", "security", "environment", "search_rescue"]

# --- Display ---
# Set True to show a live annotated camera feed window on a connected monitor.
# Works in both autonomous mode (main.py) and manual mode (manual_control.py).
SHOW_CAMERA_FEED = False
CAMERA_WINDOW_NAME = "Quadruped — Camera Feed"
