import os
from dotenv import load_dotenv

load_dotenv()

# --- Servo channels (PCA9685 channel index per joint) ---
# Ch 0  = R1 = front_right_hip
# Ch 11 = R2 = front_right_knee
# Ch 2  = L1 = front_left_hip
# Ch 3  = L2 = front_left_knee
# Ch 4  = R4 = rear_right_knee
# Ch 12 = R3 = rear_right_hip  (NOT WORKING — investigate)
# Ch 9  = L3 = rear_left_hip
# Ch 7  = L4 = rear_left_knee
SERVO_CHANNELS = {
    "front_right_hip":  0,
    "front_right_knee": 11,
    "front_left_hip":   2,
    "front_left_knee":  3,
    "rear_right_knee":  4,
    "rear_right_hip":   12,
    "rear_left_hip":    9,
    "rear_left_knee":   7,
}

# --- Per-joint angle limits (degrees) ---
# Measured from physical tuning — do not exceed these or servos will strain
SERVO_LIMITS = {
    "front_right_hip":  (50,  160),   # R1: 50=front, 160=back
    "front_right_knee": (70,  110),   # R2: 70=front, 110=back
    "front_left_hip":   (10,  120),   # L1: 10=back,  120=front
    "front_left_knee":  (80,  150),   # L2: 80=back,  150=front
    "rear_right_knee":  (30,  180),   # R4: 30=down,  180=up
    "rear_right_hip":   (90,  90),    # R3: NOT WORKING — locked at 90 for safety
    "rear_left_hip":    (30,  180),   # L3: 30=down,  180=up
    "rear_left_knee":   (0,   140),   # L4: 0=up,     140=down
}

# --- Standing pose (degrees per joint) ---
# 90° = upright for all joints
STAND_POSE = {
    "front_right_hip":  90,
    "front_right_knee": 90,
    "front_left_hip":   90,
    "front_left_knee":  90,
    "rear_right_knee":  90,
    "rear_right_hip":   90,   # R3 not working — wiring issue
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
MOCK_SERVOS = False

# --- Vision ---
CAMERA_RESOLUTION  = (640, 480)
DETECTION_CONFIDENCE_THRESHOLD = 0.4

# --- LLM ---
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
# Primary LLM (Ollama) model name. Example: "gemma4"
LLM_MODEL       = os.environ.get("CLEO_MODEL", "gemma4")

# Optional fallback LLM (Gemini)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MISSION_MAX_STEPS = 10   # max steps before giving up on a mission

VALID_ACTIONS  = [
    "walk_forward", "turn_left", "turn_right",
    "stop", "complete", "speak", "set_mode",
    "dance", "wave",
]

# --- Voice ---
WHISPER_MODEL    = "tiny.en"
TTS_LANGUAGE     = "en"
IDLE_DANCE_TIMEOUT  = 30   # seconds of silence before dancing
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # default: George
ELEVENLABS_MODEL    = "eleven_flash_v2_5"
MIC_SAMPLE_RATE       = 16000
MIC_DEVICE_INDEX      = None   # None = default USB mic
MIC_SILENCE_THRESHOLD = 0.01   # RMS below this = silence, skip transcription
MIN_WORDS_TO_PROCESS  = 2      # ignore transcripts shorter than this many words

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
# Camera feed is shown automatically when a monitor/display is detected ($DISPLAY).
# No config needed — it gracefully skips when running headless over SSH.
CAMERA_WINDOW_NAME = "Quadruped — Camera Feed"
