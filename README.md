# Quadruped Robot — Cleo

An autonomous 4-legged robot powered by a Raspberry Pi and a local Gemma 4 AI brain. Speak to it, give it missions, and it walks, looks, thinks, and talks back. Supports multiple AI personality modes switchable by voice at any time.

Gemma 4 runs locally via [Ollama](https://ollama.com) — no cloud required. Google Gemini is available as an optional fallback if Ollama is unreachable.

> For full software architecture, data flows, and code documentation see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Features

- **Voice control** — speak naturally to give missions or have a conversation
- **AI brain** — Gemma 4 (local) decides every action based on what you say and what the camera sees
- **Gemini fallback** — automatically switches to Gemini if Ollama fails, then recovers
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
| **Gemma 4 (via Ollama)** | Primary AI decision engine — runs fully locally, no API key or internet needed |
| **Google Gemini 2.5 Flash** | Optional fallback AI — activates automatically if Ollama is unavailable |
| **faster-whisper (Whisper tiny.en)** | Speech-to-text — runs fully offline on the Pi, no API key needed |
| **gTTS (Google Text-to-Speech)** | Text-to-speech — converts AI responses to audio, requires internet |
| **MobileNet SSD (OpenCV DNN)** | Object detection — runs locally on the Pi, identifies objects in camera frames |
| **USB Webcam or Pi Camera** | Captures frames for object detection |
| **PCA9685 PWM driver** | Controls all 8 servo motors over I2C |
| **luma.oled + PIL** | Draws bitmap faces on the SSD1306 OLED display |
| **Adafruit CircuitPython** | Servo motor and DHT11 sensor drivers |
| **sounddevice** | Records microphone audio |
| **pygame** | Plays TTS audio through the speaker |
| **python-dotenv** | Loads configuration securely from `.env` |

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

**To switch by voice** — say it naturally, the AI understands intent:
- *"Switch to search and rescue mode"*
- *"Go into security mode"*
- *"Back to general mode"*

---

## OLED Faces

The display shows animated bitmap faces. Each state has multiple variants that cycle randomly — no two consecutive looks the same.

| State | Variants | When shown |
|---|---|---|
| `idle` | Open eyes, half-asleep, mid-blink | Waiting for input |
| `thinking` | Squinted, looking sideways, looking up | AI is processing |
| `searching` | One-eye squint, both-eyes-wide alert | On a mission |
| `happy` | Standard smile, wink, huge eyes, star eyes, excited | Mission complete |
| `surprised` | Wide O-eyes + hollow O-mouth | Triggered manually |

---

## Setup

There are two setup paths depending on what hardware you have available:

- **[Full setup](#full-setup)** — complete robot with servos, OLED, and sensors
- **[Camera / mic / speaker only](#cameramicspeaker-only-setup)** — test voice and vision without any I2C hardware

Ollama can run on the Pi itself or on a separate machine on the same network (recommended for better performance — see [Ollama on a separate machine](#ollama-on-a-separate-machine)).

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

### 6. Install Ollama and pull Gemma 4

Install Ollama on the machine that will run inference (the Pi, or a separate computer — see note below):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4
```

Verify it works:

```bash
ollama run gemma4 "Reply with only valid JSON: {\"action\": \"speak\", \"text\": \"hello\"}"
```

> **Pi 4 note:** Gemma 4 runs on a Pi 4 but responses will take several seconds. For faster inference, run Ollama on a laptop or desktop on the same network and set `OLLAMA_BASE_URL` in `.env` to point at it (e.g. `http://192.168.1.10:11434`). See [Ollama on a separate machine](#ollama-on-a-separate-machine).

### 7. Configure `.env`

```bash
nano .env
```

Minimum config (Gemma 4 only, no fallback):
```
CLEO_MODEL=gemma4
```

With Gemini fallback enabled:
```
CLEO_MODEL=gemma4
GEMINI_API_KEY=your_key_here
```

Get a free Gemini key at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey). Save with `Ctrl+X` → `Y` → `Enter`.

### 8. Create a virtual environment and install dependencies

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
  ollama \
  python-dotenv \
  RPi.GPIO
```

To also enable the Gemini fallback:

```bash
pip install google-generativeai
```

> You must run `source venv/bin/activate` at the start of every new SSH session before running the robot.

### 9. Download the vision model

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

### 10. Test audio

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

### 11. Run

```bash
python3 main.py
```

The robot stands up and says "I'm listening."

### 12. Auto-start on boot *(optional)*

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

Follow steps 1–7 from [Full Setup](#full-setup) above (flash OS, SSH in, get the project, install Ollama, configure `.env`). Skip the raspi-config I2C step.

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
  ollama \
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
MOCK_SERVOS = True        # skips all I2C/servo/GPIO hardware
SHOW_CAMERA_FEED = False  # no display window (required when running over SSH)
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

Servo and OLED commands will print as `[MOCK]` lines. Everything else (voice, camera, AI) runs for real.

---

## Ollama on a Separate Machine

If the Pi is too slow for comfortable inference, run Ollama on a laptop or desktop on the same network and point Cleo at it.

**On the host machine:**

```bash
# Start Ollama listening on all interfaces (not just localhost)
OLLAMA_HOST=0.0.0.0 ollama serve
```

**In Cleo's `.env`:**

```
OLLAMA_BASE_URL=http://<host-ip>:11434
CLEO_MODEL=gemma4
```

Replace `<host-ip>` with the host machine's local IP (e.g. `192.168.1.10`). The Pi will send inference requests over the network — same Gemma 4 model, much faster responses.

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
| `SPACE` | Ask the AI what it currently sees — speaks the answer aloud and shows it on screen |
| `1` | Switch to General mode |
| `2` | Switch to Security mode |
| `3` | Switch to Environment mode |
| `4` | Switch to Search & Rescue mode |
| `F` | Cycle the OLED to a random happy face |
| `Q` or `ESC` | Quit cleanly |

The camera window overlays the current mode, last action, last AI response, and live sensor readings directly on the feed.

---

## Configuration Reference

| Setting | What it controls | Default |
|---|---|---|
| `CLEO_MODEL` | Ollama model name (set in `.env`) | `gemma4` |
| `OLLAMA_BASE_URL` | Ollama server URL (set in `.env`) | `http://localhost:11434` |
| `GEMINI_API_KEY` | Gemini fallback key — leave blank to disable (set in `.env`) | *(blank)* |
| `GEMINI_MODEL` | Gemini model used for fallback (set in `.env`) | `gemini-2.5-flash` |
| `WHISPER_MODEL` | STT model size | `tiny.en` |
| `MIC_DEVICE_INDEX` | USB mic card number (`None` = auto) | `None` |
| `CAMERA_RESOLUTION` | Capture resolution | `(640, 480)` |
| `DETECTION_CONFIDENCE_THRESHOLD` | Min confidence to report an object | `0.5` |
| `SHOW_CAMERA_FEED` | Show annotated feed on monitor (disable over SSH) | `False` |
| `MOCK_SERVOS` | Skip all I2C/servo/GPIO hardware | `True` |
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
- Gemma 4 runs entirely locally — no speech, sensor data, or commands leave your network
- `GEMINI_API_KEY` is optional and defaults to blank — if absent, Gemini fallback is silently disabled
- Never paste API keys into chat, issues, or log files
- `robot.log` does not record API keys or audio transcripts

---

## Known Limitations

- **gTTS needs internet** — for fully offline TTS, swap `gTTS` for `pyttsx3` in `voice/tts.py`
- **Whisper has a 1–2s delay** — after you stop speaking, transcription takes a moment on Pi 4
- **Gemma 4 on Pi 4 is slow** — run Ollama on a separate machine for real-time feel
- **MobileNet SSD recognises 20 object classes only** — it cannot identify objects outside that list
- **Chat history is in-memory** — resets on restart or mode change
- **`SHOW_CAMERA_FEED = True` crashes over SSH** — set it to `False` when running headless
- **Gemini fallback requires `google-generativeai`** — install it separately if you want the fallback
