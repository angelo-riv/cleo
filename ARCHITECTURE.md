# Software Architecture

Technical documentation for the quadruped robot codebase — data flows, execution loops, component responsibilities, and design decisions.

> For setup instructions, hardware, features, and demo controls see [README.md](README.md).

---

## System Layers

```
╔══════════════════════════════════════════════════════════════════╗
║                         YOU (the human)                          ║
║                  speak ↓              ↑ hear                     ║
╚══════════════════════════╤═══════════════════════════════════════╝
                           │
╔══════════════════════════▼═══════════════════════════════════════╗
║                      HARDWARE LAYER                              ║
║                                                                  ║
║  [USB Mic] [Pi Camera] [PIR Sensor] [DHT11] [Speaker]           ║
║  [8x Servos via PCA9685]  [SSD1306 OLED]                        ║
╚══════════════════════════╤═══════════════════════════════════════╝
                           │ GPIO / I2C / CSI / USB
╔══════════════════════════▼═══════════════════════════════════════╗
║                      SOFTWARE LAYER (Python)                     ║
║                                                                  ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │                    brain/agent.py                         │   ║
║  │             (master orchestrator — runs forever)          │   ║
║  └───┬──────────┬───────────┬──────────┬──────────┬─────────┘   ║
║      │          │           │          │          │              ║
║  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼──────────┐ ║
║  │voice/ │  │vision/│  │motion/│  │display│  │  modules/    │ ║
║  │stt.py │  │detect │  │gait.py│  │oled.py│  │  pir.py      │ ║
║  │tts.py │  │or.py  │  │servo_ │  │faces/ │  │  dht11.py    │ ║
║  │       │  │       │  │ctrl.py│  │       │  │  detector.py │ ║
║  └───┬───┘  └───┬───┘  └───────┘  └───────┘  └──────────────┘ ║
║      │          │                                               ║
║  ┌───▼──────────▼─────────────────────────────────────────┐    ║
║  │                    brain/llm.py                         │    ║
║  │   (packages inputs → sends to Gemini → parses JSON)    │    ║
║  └───────────────────────────┬─────────────────────────────┘   ║
╚══════════════════════════════╤══════════════════════════════════╝
                               │ HTTPS (Gemini API)
╔══════════════════════════════▼═══════════════════════════════════╗
║                      GOOGLE GEMINI (cloud AI)                    ║
║   Receives: user speech + camera detections + sensor readings    ║
║   Returns:  one JSON action  e.g. {"action": "walk_forward"}     ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Project Structure

```
quadruped/
├── main.py                  # Entry point — creates and runs Agent
├── manual_control.py        # Demo mode — keyboard control + live camera feed
├── config.py                # All settings, loaded from .env + hardware constants
├── setup.sh                 # One-time install script for Raspberry Pi
├── .env                     # Secret API keys (never committed)
├── .gitignore               # Excludes .env, model weights, pycache
│
├── brain/
│   ├── agent.py             # Master orchestrator — boot, main loop, mission loop
│   └── llm.py               # Gemini: mode prompts, persistent chat session, JSON parsing
│
├── motion/
│   ├── servo_controller.py  # Low-level: sets angles on individual joints via PCA9685
│   └── gait.py              # High-level: coordinates 4 legs for walking and turning
│
├── vision/
│   └── detector.py          # Pi Camera + MobileNet SSD: detects objects with position
│
├── voice/
│   ├── stt.py               # USB mic → Whisper AI → text (fully offline)
│   └── tts.py               # Text → Google TTS → speaker audio
│
├── display/
│   ├── oled.py              # Renders bitmap faces on SSD1306 OLED, random variant selection
│   └── faces/
│       ├── idle.py          # Open eyes, flat mouth
│       ├── idle_sleepy.py   # Half-closed eyes
│       ├── idle_blink.py    # Mid-blink slit eyes
│       ├── thinking.py      # Squinted eyes
│       ├── thinking_sideways.py  # Eyes shifted right
│       ├── thinking_up.py   # Eyes shifted upward
│       ├── searching.py     # One wide, one squinted
│       ├── searching_alert.py    # Both eyes wide open
│       ├── happy.py         # Standard smile
│       ├── happy_wink.py    # Wink + smile
│       ├── happy_big.py     # Oversized eyes + wide smile
│       ├── happy_star.py    # Cross/star-shaped eyes + smile
│       ├── excited.py       # Eyebrows + big eyes + extra-wide smile
│       └── surprised.py     # Huge square eyes + hollow O-mouth
│
├── modules/
│   ├── detector.py          # I2C bus scan at boot → returns starting mode string
│   ├── dht11.py             # DHT11 driver → {temperature, humidity}
│   └── pir.py               # PIR driver → motion_detected bool
│
└── utils/
    └── logger.py            # Colour-coded terminal logger with timestamps and levels
```

---

## Component Responsibilities

| File | Role | Inputs | Outputs |
|---|---|---|---|
| `main.py` | Entry point | — | Creates and runs `Agent` |
| `brain/agent.py` | Orchestrator | All sensor/voice/vision data | Commands to all subsystems |
| `brain/llm.py` | AI interface | Speech + detections + sensor data + mode | JSON action dict |
| `voice/stt.py` | Speech-to-text | USB mic audio (5s window) | Transcribed string |
| `voice/tts.py` | Text-to-speech | String | Audio played through speaker |
| `vision/detector.py` | Object detection | Camera frame | `[{label, position, confidence, bbox}]` |
| `motion/servo_controller.py` | Joint control | Joint name + angle | PWM signal via PCA9685 |
| `motion/gait.py` | Walking | Action string | Sequence of joint angle commands |
| `display/oled.py` | Face display | Face state string | Bitmap rendered to OLED |
| `modules/detector.py` | Mode detection | I2C bus scan | Mode string |
| `modules/pir.py` | Motion sensing | GPIO pin 17 | `True` / `False` |
| `modules/dht11.py` | Environment sensing | GPIO pin 27 | `{temperature, humidity}` |
| `utils/logger.py` | Logging | Message + level string | Colour-coded terminal line |
| `config.py` | Configuration | `.env` file | Constants used by all modules |

---

## Boot Sequence

```
python3 main.py
       │
       ▼
Agent.__init__()
       │
       ├──► ServoController()
       │         └── Connects to PCA9685 over I2C (address 0x40)
       │         └── Creates 8 servo objects (hips + knees for each leg)
       │
       ├──► GaitController(servo_controller)
       │         └── Stores servo reference, loads standing pose from config
       │
       ├──► VisionDetector()
       │         └── Loads MobileNet SSD model files into OpenCV DNN
       │         └── Starts Raspberry Pi Camera via picamera2
       │
       ├──► OLEDDisplay()
       │         └── Connects to SSD1306 over I2C (address 0x3C)
       │
       ├──► SpeechToText()
       │         └── Loads Whisper "tiny.en" model into CPU memory (~75MB)
       │
       ├──► TextToSpeech()
       │         └── Initialises pygame audio mixer
       │
       ├──► ModuleDetector()
       │         └── Scans I2C bus for known addresses
       │         └── Returns: "environment" (DHT11) | "security" (default)
       │
       ├──► PIRSensor()   [optional — skipped gracefully if absent]
       │         └── Configures GPIO pin 17 as input
       │
       └──► DHT11Sensor() [optional — skipped gracefully if absent]
                 └── Configures GPIO pin 27 as input

Agent.run()
       │
       ├──► sc.stand()              → all 8 servos go to standing pose
       ├──► oled.show("idle")       → OLED renders idle face variant
       ├──► module.detect()         → returns active mode string
       ├──► llm.reset_session(mode) → creates Gemini chat session with mode prompt
       └──► tts.speak("Ready. [mode] mode active.")
```

---

## Main Loop (idle / conversation)

Runs forever after boot. The robot stays here until Gemini returns a movement action.

```
                    ┌──────────────────────────────────┐
                    │         MAIN LOOP (forever)       │
                    └──────────────────┬───────────────┘
                                       │
                              oled.show("idle")
                                       │
                         tts.speak("I'm listening.")
                         [first pass only, or after
                          mission / mode switch ends]
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │  stt.listen(duration=5)  │
                         │  USB mic records 5 secs  │
                         │  Whisper transcribes it  │
                         └───────────┬─────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  user_input empty?   │
                          └──────────┬──────────┘
                              yes ◄──┴──► no
                               │              │
                    [refresh camera feed]  oled.show("thinking")
                    [if SHOW_CAMERA_FEED]       │
                    [then loop back]    ┌───────▼────────────────┐
                                        │  _detect()             │
                                        │  Camera captures frame │
                                        │  MobileNet runs        │
                                        │  Frame shown on monitor│
                                        │  if SHOW_CAMERA_FEED   │
                                        └───────┬────────────────┘
                                                │
                                        ┌───────▼────────────────┐
                                        │  _read_sensors()        │
                                        │  PIR → motion: bool     │
                                        │  DHT11 → temp, humidity │
                                        └───────┬────────────────┘
                                                │
                                        ┌───────▼────────────────┐
                                        │  llm.decide(           │
                                        │    user_input,          │
                                        │    detections,          │
                                        │    mode,                │
                                        │    sensor_data          │
                                        │  )                     │
                                        │                        │
                                        │  Message sent:         │
                                        │  "Input: [speech]      │
                                        │   Camera sees: [objs]  │
                                        │   Sensors: [readings]" │
                                        │                        │
                                        │  Gemini replies: JSON  │
                                        │  History preserved in  │
                                        │  chat session          │
                                        └───────┬────────────────┘
                                                │
                                   ┌────────────▼────────────────┐
                                   │  action = decision["action"] │
                                   └──┬──────┬──────┬──────┬─────┘
                                      │      │      │      │
                                   "speak" "set_ "stop" movement
                                      │    mode"    │   action
                                      │      │      │      │
                                tts.speak() │  sc.stand()  │
                                      │  switch    │  _run_mission()
                                      │  mode +    │
                                      │  new chat  │
                                      │  session   │
                                      └─────┴──────┘
                                             │
                                          (loop back)
```

---

## Mission Execution Flow

Triggered when Gemini returns a movement action. The robot navigates autonomously, querying Gemini every step, until `complete` or 30 steps.

```
_run_mission(mission, mode, first_action)
       │
       ├──► oled.show("searching")
       ├──► gait.execute(first_action)   ← first action already decided, run immediately
       │
       │         ┌────────────────────────────────────────────┐
       │         │      MISSION LOOP (up to 29 more steps)     │
       │         └──────────────────┬─────────────────────────┘
       │                            │
       │                   oled.show("thinking")
       │                            │
       │             ┌──────────────▼──────────────┐
       │             │  _detect()                   │
       │             │  _read_sensors()             │
       │             │  llm.decide(...)             │
       │             │  → full chat history + new   │
       │             │    frame + live sensor data  │
       │             └──────────────┬──────────────┘
       │                            │
       │             ┌──────────────▼──────────────┐
       │             │    action?                   │
       │             └──┬──────┬──────┬──────┬──────┘
       │                │      │      │      │
       │           "complete" "speak" "set_ movement
       │                │      │      mode"  │
       │                │      │      │      │
       │          oled("happy")│  switch  gait.execute()
       │          tts("Mission"│  mode    oled("searching")
       │             complete")│  return  (next step)
       │          sc.stand()   │
       │          return mode  │
       │                  tts.speak(text)
       │                  oled("searching")
       │                  (continue loop)
       │
       └──► [30 steps, no complete]
                 tts.speak("I could not complete the mission.")
                 sc.stand()
                 oled.show("idle")
                 return mode
```

---

## Mode Switching Flow

Triggered by voice from either the main loop or mid-mission. Gemini issues the `set_mode` action itself based on what you say.

```
You say: "Switch to search and rescue mode"
                    │
                    ▼
          llm.decide() → Gemini sees speech + camera + sensors
                    │
                    ▼
          Gemini returns:
          {
            "action": "set_mode",
            "mode":   "search_rescue",
            "text":   "Switching to search and rescue mode."
          }
                    │
                    ▼
          agent._handle_set_mode()
                    │
                    ├──► tts.speak(text)
                    ├──► llm.reset_session("search_rescue")
                    │         └── New Gemini chat session
                    │         └── System prompt: emergency responder personality
                    │         └── Previous history cleared
                    └──► mode = "search_rescue"
```

---

## What Gemini Receives Each Step

Every `llm.decide()` call sends one text message into the persistent chat session:

```
Input: find the person
Camera sees: person (center), bottle (left)
Sensor readings: PIR motion detected: True | Temperature: 24.5°C | Humidity: 55.0%
```

Gemini replies with exactly one JSON object chosen from the valid action set:

```json
{"action": "walk_forward"}
{"action": "speak", "text": "I see a person ahead, should I approach?"}
{"action": "complete"}
{"action": "set_mode", "mode": "search_rescue", "text": "Switching to search and rescue mode."}
```

Valid actions: `walk_forward`, `turn_left`, `turn_right`, `stop`, `complete`, `speak`, `set_mode`

The chat session retains full message history — Gemini has context about everything said and seen since the session started or last mode switch.

---

## Mode Prompts

Each mode gives Gemini a distinct system prompt loaded at session creation. All share the same base navigation and response format rules.

| Mode | Personality |
|---|---|
| `general` | Helpful curious companion. Navigates on request, converses freely. |
| `security` | Vigilant patrol robot. Treats unknowns as threats. Reports motion immediately. Brief, professional responses. |
| `environment` | Analytical environmental monitor. Always acknowledges sensor readings. Flags anomalies (temp > 35°C / < 10°C, humidity > 80% / < 20%). |
| `search_rescue` | Emergency responder. Systematic scan pattern. Never declares complete until a person is centered in frame. Life-or-death urgency. |

---

## Vision Pipeline

The camera never sends images to Gemini. All computer vision runs locally on the Pi.

```
1. Camera captures one frame (640×480)
        │
        ▼
2. Frame resized to 300×300 and normalised
        │
        ▼
3. MobileNet SSD runs on Pi CPU
   → bounding boxes + class labels + confidence scores
        │
        ▼
4. Results filtered: confidence must exceed threshold (default 0.5)
        │
        ▼
5. Horizontal center of each box determines position:
   cx < 213px  → "left"
   cx > 427px  → "right"
   otherwise   → "center"
        │
        ▼
6. Returns: [{"label": "person", "position": "center", "confidence": 0.87, "bbox": (x1,y1,x2,y2)}]
        │
        ▼
7. Agent converts to plain text → sent to Gemini as part of the message
```

**If `SHOW_CAMERA_FEED = True`:** bounding boxes, labels, confidence scores, and position zone markers are drawn onto the frame and displayed in a resizable OpenCV window.

### Detectable Object Classes (MobileNet SSD)

`person`, `bird`, `cat`, `dog`, `horse`, `cow`, `sheep`, `bottle`, `chair`, `sofa`, `diningtable`, `pottedplant`, `tvmonitor`, `car`, `bus`, `bicycle`, `motorbike`, `boat`, `aeroplane`, `train`

---

## Gait Mechanics

Each leg has two servo joints — a **hip** (swings the leg forward/backward) and a **knee** (lifts the foot). The creep gait moves one leg at a time so three legs are always on the ground.

```
Step order: front_left → rear_right → front_right → rear_left  (repeat)

Each leg per step:
  1. Knee lifts    — foot leaves ground
  2. Hip swings    — leg moves in direction of travel
  3. Knee plants   — foot returns to ground
  4. Hip returns   — neutral position, body weight shifts
```

Turning rotates the body in place: one side swings backward while the other swings forward.

---

## OLED Face System

Each face file defines a `BITMAP` — a list of `(x1, y1, x2, y2)` rectangle coordinates on a 128×64 pixel canvas.

`oled.show(state)` works as follows:
1. Looks up the face group for the requested state
2. Picks a random variant from the group, avoiding the previous one
3. Creates a blank 1-bit PIL image (all black)
4. Draws each rectangle as white pixels
5. Pushes the image to the SSD1306 display over I2C

Face groups and their variants:

| State | Variants |
|---|---|
| `idle` | `idle`, `idle_sleepy`, `idle_blink` |
| `thinking` | `thinking`, `thinking_sideways`, `thinking_up` |
| `searching` | `searching`, `searching_alert` |
| `happy` | `happy`, `happy_wink`, `happy_big`, `happy_star`, `excited` |
| `surprised` | `surprised` |

---

## Speech Systems

### STT — Speech to Text (`voice/stt.py`)
- Uses `faster-whisper` running the `tiny.en` Whisper model locally on the Pi CPU
- Records 5 seconds of audio via `sounddevice` from the USB microphone
- Transcribes entirely offline — no internet, no API key
- Model is downloaded once (~75MB) during setup
- Typical transcription time on Pi 4: 1–2 seconds after recording ends

### TTS — Text to Speech (`voice/tts.py`)
- Uses `gTTS` (Google Text-to-Speech) — sends text to Google's servers, receives an MP3
- Plays audio through the speaker via `pygame.mixer`
- **Requires internet connection** — no API key needed
- For fully offline TTS, replace with `pyttsx3` in `voice/tts.py`

---

## Security

- `.env` is in `.gitignore` and will never be committed
- `config.py` uses `os.environ["GEMINI_API_KEY"]` — crashes immediately on startup if key is missing
- No API keys or audio content are written to `robot.log`
- Sensor readings and Gemini responses are logged at DEBUG level only

---

## Known Limitations

- **gTTS requires internet** — swap for `pyttsx3` in `voice/tts.py` for offline operation
- **Whisper STT has 1–2s delay** — after speaking stops, transcription takes time on Pi 4
- **MobileNet SSD is fixed at 20 classes** — cannot identify objects outside the trained set
- **Gemini chat history is in-memory only** — resets on restart or mode switch
- **Vision is frame-by-frame** — no continuous video stream; camera only samples during decision steps
