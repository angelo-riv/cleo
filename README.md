# Quadruped Robot

An autonomous 4-legged robot powered by a Raspberry Pi and Google Gemini AI. Speak to it, give it missions, and it walks, looks, thinks, and talks back. Supports multiple AI personality modes switchable by voice at any time.

> For full software architecture, data flows, and code documentation see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Features

- **Voice control** — speak naturally to give missions or have a conversation
- **AI brain** — Google Gemini decides every action based on what you say and what the camera sees
- **Object detection** — camera identifies 20 object types and their position (left / center / right)
- **Walking** — creep gait using 8 servo motors across 4 legs
- **Expressive face** — OLED display shows animated faces that change based on what the robot is doing
- **Sensor awareness** — live temperature, humidity, and motion data fed to the AI
- **Switchable modes** — say "switch to search and rescue mode" and the AI's entire personality changes
- **Manual control** — keyboard-driven demo mode with live annotated camera feed for presentations

---

## Technologies Used

| Technology | What it does in this project |
|---|---|
| **Python 3** | Entire codebase |
| **Google Gemini 2.5 Flash** | AI decision engine — receives text descriptions of what the robot sees and returns the next action as JSON |
| **faster-whisper (Whisper tiny.en)** | Speech-to-text — runs fully offline on the Pi, no API key needed |
| **gTTS (Google Text-to-Speech)** | Text-to-speech — converts Gemini's responses to audio, requires internet |
| **MobileNet SSD (OpenCV DNN)** | Object detection — runs locally on the Pi, identifies objects in camera frames |
| **USB Webcam or Pi Camera** | Captures frames for object detection |
| **PCA9685 PWM driver** | Controls all 8 servo motors over I2C |
| **luma.oled + PIL** | Draws bitmap faces on the SSD1306 OLED display |
| **Adafruit CircuitPython** | Servo motor and DHT11 sensor drivers |
| **sounddevice** | Records microphone audio |
| **pygame** | Plays TTS audio through the speaker |
| **python-dotenv** | Loads API keys securely from `.env` |

---

## Hardware Required

| Part | Purpose |
|---|---|
| Raspberry Pi 4 (or 3B+) | Main computer |
| PCA9685 PWM driver board | Controls 8 servos over I2C |
| 8x servo motors | 2 per leg — hip + knee |
| USB webcam or Pi Camera Module | Object detection |
| USB microphone | Voice input |
| Speaker + USB audio adapter | Voice output |
| SSD1306 OLED display (128×64) | Face display |
| DHT11 sensor *(optional)* | Activates environment mode |
| PIR motion sensor *(optional)* | Activates security mode |
| 5V power supply | Pi + servos (servos draw significant current) |

### Wiring

| Component | Connection |
|---|---|
| PCA9685 | I2C — SDA = GPIO 2, SCL = GPIO 3, address `0x40` |
| OLED display | I2C — same bus, address `0x3C` |
| DHT11 | GPIO pin 27 |
| PIR sensor | GPIO pin 17 |
| USB webcam | Any USB port |
| USB mic + speaker | USB ports |

---

## Modes

The robot scans for attached sensor modules at boot and starts in the matching mode. Switch anytime by voice.

| Mode | Activates when | AI personality |
|---|---|---|
| `general` | No module detected | Helpful companion, conversational |
| `security` | PIR sensor on GPIO 17 | Vigilant patrol robot, threat-aware |
| `environment` | DHT11 on I2C `0x44` | Environmental monitor, flags temp/humidity anomalies |
| `search_rescue` | Voice command only | Emergency responder, systematic people-search |

**To switch by voice** — say it naturally, Gemini understands intent:
- *"Switch to search and rescue mode"*
- *"Go into security mode"*
- *"Back to general mode"*

---

## OLED Faces

The display shows animated bitmap faces. Each state has multiple variants that cycle randomly — no two consecutive looks the same.

| State | Variants | When shown |
|---|---|---|
| `idle` | Open eyes, half-asleep, mid-blink | Waiting for input |
| `thinking` | Squinted, looking sideways, looking up | Gemini is processing |
| `searching` | One-eye squint, both-eyes-wide alert | On a mission |
| `happy` | Standard smile, wink, huge eyes, star eyes, excited | Mission complete |
| `surprised` | Wide O-eyes + hollow O-mouth | Triggered manually |

---

## Setup

There are two setup paths depending on what hardware you have available:

- **[Full setup](#full-setup)** — complete robot with servos, OLED, and sensors
- **[Camera / mic / speaker only](#cameramicspeaker-only-setup)** — test voice and vision without any I2C hardware

---

## Full Setup

### 1. Flash Raspberry Pi OS

Use **Raspberry Pi Imager** → **Raspberry Pi OS (64-bit)**. In the advanced settings (gear icon):
- Set hostname, username, password
- Enable SSH
- Enter your Wi-Fi credentials

### 2. SSH into the Pi

Find the Pi's IP address from your router's device list, or from the Pi directly if you have a monitor:

```bash
hostname -I
```

Then connect from your computer:

```bash
ssh <username>@<ip-address>
# Example: ssh pi@192.168.1.42
```

If you set a hostname in Raspberry Pi Imager (e.g. `quadruped`), you can also use:

```bash
ssh <username>@quadruped.local
```

Accept the fingerprint prompt the first time. Enter the password you set in Imager.

> **Windows users** — SSH is built into PowerShell and Command Prompt on Windows 10+. No extra software needed.

### 3. Enable I2C

```bash
sudo raspi-config
```

Under **Interface Options** enable **I2C**, then reboot:

```bash
sudo reboot
```

### 4. Get the project

```bash
git clone <your-repo-url> ~/quadruped
cd ~/quadruped
```

### 5. Set up SSH key for GitHub (if cloning via SSH)

```bash
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub
```

Copy the output and add it to GitHub under **Settings → SSH and GPG keys → New SSH key**.

Verify it works:

```bash
ssh -T git@github.com
```

### 6. Configure `.env` (Gemma 4 primary, Gemini optional fallback)

```bash
nano .env
```

```
# Primary (Ollama / Gemma 4)
CLEO_MODEL=gemma4
OLLAMA_BASE_URL=http://localhost:11434

# Optional fallback (Gemini) — only used if Ollama fails
# GEMINI_API_KEY=your_actual_key_here
# GEMINI_MODEL=gemini-2.5-flash
```

If you want the Gemini fallback, get a free key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey). Save with `Ctrl+X` → `Y` → `Enter`.

### 7. Create a virtual environment and install dependencies

Raspberry Pi OS Trixie requires a venv — do not skip this:

```bash
python3 -m venv venv
source venv/bin/activate

sudo apt update
sudo apt install -y python3-dev portaudio19-dev libgpiod2

pip install \
  adafruit-circuitpython-pca9685 \
  adafruit-circuitpython-motor \
  adafruit-circuitpython-dht \
  opencv-python \
  luma.oled \
  Pillow \
  faster-whisper \
  sounddevice \
  gTTS \
  pygame \
  python-dotenv \
  RPi.GPIO
```

To enable the optional Gemini fallback:

```bash
pip install google-generativeai
```

> You must run `source venv/bin/activate` at the start of every new SSH session before running the robot.

### 8. Download the vision model

```bash
mkdir -p models

# Prototxt (~29 KB)
wget -O models/MobileNetSSD_deploy.prototxt \
  https://raw.githubusercontent.com/djmv/MobilNet_SSD_opencv/master/MobileNetSSD_deploy.prototxt

# Caffemodel (~23 MB) — use gdown for reliable Google Drive download
pip install gdown
gdown --id 0B3gersZ2cHIxRm5PMWRoTkdHdHc -O models/MobileNetSSD_deploy.caffemodel
```

Verify both files downloaded correctly:

```bash
ls -lh models/
# prototxt should be ~29K, caffemodel should be ~23M
```

### 9. Test audio

```bash
arecord -l    # list recording devices
aplay -l      # list playback devices
```

Test record and playback using the specific card numbers shown:

```bash
arecord -D plughw:<mic-card>,0 -d 3 -f cd test.wav && aplay -D plughw:<speaker-card>,0 test.wav
```

Set the default speaker so pygame picks it up:

```bash
nano ~/.asoundrc
```

```
defaults.pcm.card <speaker-card>
defaults.ctl.card <speaker-card>
```

If the wrong mic is selected, set `MIC_DEVICE_INDEX` in `config.py` to the correct card number.

### 10. Run

```bash
python3 main.py
```

The robot stands up and says "I'm listening."

### 11. Auto-start on boot *(optional)*

```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:

```bash
cd /home/pi/quadruped && source venv/bin/activate && python3 main.py >> /home/pi/quadruped/robot.log 2>&1 &
```

---

## Camera / Mic / Speaker Only Setup

Use this path to test voice and vision without any I2C hardware (no servo driver, no OLED, no sensors). The robot runs in mock mode — servo and display commands print to the terminal instead of hitting hardware.

### 1. Flash, SSH, and get the project

Follow steps 1–6 from [Full Setup](#full-setup) above (flash OS, SSH in, get the project, add API key). Skip the raspi-config I2C step.

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate

sudo apt update
sudo apt install -y python3-dev portaudio19-dev

pip install \
  opencv-python \
  luma.oled \
  Pillow \
  faster-whisper \
  sounddevice \
  gTTS \
  pygame \
  google-generativeai \
  python-dotenv
```

### 3. Download the vision model

```bash
mkdir -p models

wget -O models/MobileNetSSD_deploy.prototxt \
  https://raw.githubusercontent.com/djmv/MobilNet_SSD_opencv/master/MobileNetSSD_deploy.prototxt

pip install gdown
gdown --id 0B3gersZ2cHIxRm5PMWRoTkdHdHc -O models/MobileNetSSD_deploy.caffemodel
```

Verify sizes (`prototxt` ~29K, `caffemodel` ~23M):

```bash
ls -lh models/
```

### 4. Enable mock mode

Open `config.py` and set:

```python
MOCK_SERVOS = True      # skips all I2C/servo/GPIO hardware
SHOW_CAMERA_FEED = False  # no display window (required when running over SSH)
CLEO_MODEL = "gemma4"
OLLAMA_BASE_URL = "http://localhost:11434"
# Optional fallback:
# GEMINI_API_KEY = "..."
# GEMINI_MODEL = "gemini-2.5-flash"
```

### 5. Test audio

```bash
arecord -l    # find your mic card number
aplay -l      # find your speaker card number
```

```bash
arecord -D plughw:<mic-card>,0 -d 3 -f cd test.wav && aplay -D plughw:<speaker-card>,0 test.wav
```

Set the default speaker:

```bash
nano ~/.asoundrc
```

```
defaults.pcm.card <speaker-card>
defaults.ctl.card <speaker-card>
```

Set `MIC_DEVICE_INDEX` in `config.py` to your mic's card number if needed.

### 6. Test camera and object detection

```bash
python3 -c "
import cv2

net = cv2.dnn.readNetFromCaffe('models/MobileNetSSD_deploy.prototxt', 'models/MobileNetSSD_deploy.caffemodel')
CLASSES = ['background','aeroplane','bicycle','bird','boat','bottle','bus','car',
           'cat','chair','cow','diningtable','dog','horse','motorbike','person',
           'pottedplant','sheep','sofa','train','tvmonitor']

cam = cv2.VideoCapture(0)
ret, frame = cam.read()
if not ret:
    print('ERROR: camera not readable')
else:
    print(f'Frame captured: {frame.shape}')
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300,300)), 0.007843, (300,300), 127.5)
    net.setInput(blob)
    out = net.forward()
    found = [(CLASSES[int(out[0,0,i,1])], f'{out[0,0,i,2]:.0%}')
             for i in range(out.shape[2]) if out[0,0,i,2] > 0.5]
    print('Detections:', found if found else 'nothing above 50% confidence')
cam.release()
"
```

### 7. Run

```bash
python3 main.py
```

Servo and OLED commands will print as `[MOCK]` lines. Everything else (voice, camera, Gemini) runs for real.

---

## Running the Demo (Manual Control)

For presentations and demos, run `manual_control.py` instead of `main.py`. This opens a live annotated camera window on a connected monitor and lets you drive the robot with your keyboard.

```bash
python3 manual_control.py
```

> Manual control requires a connected monitor — it cannot run headless over SSH.

**Click the camera window first to capture keyboard focus, then use these controls:**

| Key | Action |
|---|---|
| `W` | Walk forward one step |
| `A` | Turn left |
| `D` | Turn right |
| `S` | Stand / stop |
| `SPACE` | Ask Gemini what it currently sees — speaks the answer aloud and shows it on screen |
| `1` | Switch to General mode |
| `2` | Switch to Security mode |
| `3` | Switch to Environment mode |
| `4` | Switch to Search & Rescue mode |
| `F` | Cycle the OLED to a random happy face |
| `Q` or `ESC` | Quit cleanly |

The camera window overlays the current mode, last action, last LLM response, and live sensor readings directly on the feed.

---

## Configuration Reference

| Setting | What it controls | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama server URL (primary LLM) | `http://localhost:11434` |
| `CLEO_MODEL` | Ollama model name (primary LLM) | `gemma4` |
| `GEMINI_API_KEY` | Enables Gemini fallback if set | *(blank)* |
| `GEMINI_MODEL` | Gemini model used for fallback | `gemini-2.5-flash` |
| `WHISPER_MODEL` | STT model size | `tiny.en` |
| `MIC_DEVICE_INDEX` | USB mic card number (`None` = auto) | `None` |
| `CAMERA_RESOLUTION` | Capture resolution | `(640, 480)` |
| `DETECTION_CONFIDENCE_THRESHOLD` | Min confidence to report an object | `0.5` |
| `SHOW_CAMERA_FEED` | Show annotated feed on monitor (disable over SSH) | `True` |
| `MOCK_SERVOS` | Skip all I2C/servo/GPIO hardware | `False` |
| `GAIT_STEP_ANGLE` | Hip swing per step (degrees) | `20` |
| `GAIT_LIFT_ANGLE` | Knee lift per step (degrees) | `30` |
| `GAIT_STEP_DELAY` | Pause between gait phases (seconds) | `0.15` |
| `PCA9685_ADDRESS` | I2C address of servo driver | `0x40` |
| `OLED_I2C_ADDRESS` | I2C address of OLED | `0x3C` |
| `PIR_GPIO_PIN` | GPIO pin for PIR sensor | `17` |
| `DHT11_GPIO_PIN` | GPIO pin for DHT11 sensor | `27` |

---

## Security Notes

- `.env` is in `.gitignore` — it will never be committed
- Gemini fallback is optional — if `GEMINI_API_KEY` is missing, the robot still runs (Gemma 4 via Ollama only)
- Never paste your API key into chat, issues, or log files
- `robot.log` does not record API keys or audio transcripts

---

## Known Limitations

- **gTTS needs internet** — for fully offline TTS, swap `gTTS` for `pyttsx3` in `voice/tts.py`
- **Whisper has a 1–2s delay** — after you stop speaking, transcription takes a moment on Pi 4
- **MobileNet SSD recognises 20 object classes only** — it cannot identify objects outside that list
- **LLM chat history is in-memory** — resets on restart or mode change
- **`SHOW_CAMERA_FEED = True` crashes over SSH** — set it to `False` when running headless
