"""
Manual Control — Demo interface for judges / presentations.

Run this INSTEAD of main.py when you want manual control.
Shows a live annotated camera feed on the connected monitor.
Keyboard controls let you move the robot, query Gemini, and switch modes.

Usage:
    python3 manual_control.py

Controls (click the camera window first to capture keyboard focus):
    W          Walk forward one step
    A          Turn left
    D          Turn right
    S          Stand / stop
    SPACE      Ask Gemini: "What do you see?" — speaks and displays the answer
    1          Switch to general mode
    2          Switch to security mode
    3          Switch to environment mode
    4          Switch to search & rescue mode
    F          Cycle OLED to a random happy face
    Q / ESC    Quit
"""

import sys
import cv2
import numpy as np

import config
from motion.servo_controller import ServoController
from motion.gait import GaitController
from vision.detector import VisionDetector
from display.oled import OLEDDisplay
from voice.tts import TextToSpeech
from modules.pir import PIRSensor
from modules.dht11 import DHT11Sensor
from brain import llm
from utils.logger import log

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW = "Quadruped — Manual Control"

MODE_KEYS = {
    ord('1'): "general",
    ord('2'): "security",
    ord('3'): "environment",
    ord('4'): "search_rescue",
}

CONTROLS_TEXT = [
    "W  — Walk forward",
    "A  — Turn left",
    "D  — Turn right",
    "S  — Stand / stop",
    "SPACE — Ask Gemini",
    "1  — General mode",
    "2  — Security mode",
    "3  — Environment mode",
    "4  — Search & rescue",
    "F  — Happy face",
    "Q/ESC — Quit",
]

# Overlay colours (BGR)
_PANEL_BG    = (20, 20, 20)
_TEXT_COLOUR = (220, 220, 220)
_KEY_COLOUR  = (80, 220, 80)
_MODE_COLOUR = (0, 200, 255)
_RESP_COLOUR = (255, 200, 80)
_WARN_COLOUR = (0, 80, 255)


# ---------------------------------------------------------------------------
# Overlay drawing helpers
# ---------------------------------------------------------------------------

def _draw_panel(img: np.ndarray, x: int, y: int, w: int, h: int, alpha: float = 0.6):
    """Draw a semi-transparent dark rectangle."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), _PANEL_BG, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def _put(img, text, pos, colour=_TEXT_COLOUR, scale=0.45, thickness=1):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, colour, thickness, cv2.LINE_AA)


def _draw_controls(img: np.ndarray):
    """Draw the keyboard controls legend in the top-right corner."""
    panel_x = img.shape[1] - 220
    panel_h = len(CONTROLS_TEXT) * 18 + 28
    _draw_panel(img, panel_x - 8, 4, 224, panel_h)
    _put(img, "CONTROLS", (panel_x, 20), _KEY_COLOUR, 0.5, 1)
    for i, line in enumerate(CONTROLS_TEXT):
        _put(img, line, (panel_x, 38 + i * 18))


def _draw_status(img: np.ndarray, mode: str, last_response: str, last_action: str):
    """Draw current mode, last action, and last Gemini response at the bottom."""
    h, w = img.shape[:2]
    _draw_panel(img, 0, h - 70, w, 70)
    _put(img, f"MODE: {mode.upper().replace('_', ' ')}", (10, h - 52), _MODE_COLOUR, 0.5, 1)
    _put(img, f"LAST ACTION: {last_action}", (10, h - 34), _KEY_COLOUR, 0.45)
    # Wrap long response text
    response_display = last_response[:90] + "…" if len(last_response) > 90 else last_response
    _put(img, f"GEMINI: {response_display}", (10, h - 14), _RESP_COLOUR, 0.42)


def _draw_sensor_overlay(img: np.ndarray, sensor_data: dict):
    """Draw live sensor readings in bottom-right if present."""
    if not sensor_data:
        return
    lines = []
    if "motion_detected" in sensor_data:
        colour = _WARN_COLOUR if sensor_data["motion_detected"] else _TEXT_COLOUR
        lines.append(("MOTION DETECTED!" if sensor_data["motion_detected"] else "No motion", colour))
    if "temperature" in sensor_data:
        lines.append((f"Temp: {sensor_data['temperature']}°C", _TEXT_COLOUR))
    if "humidity" in sensor_data:
        lines.append((f"Humidity: {sensor_data['humidity']}%", _TEXT_COLOUR))
    if not lines:
        return
    h, w = img.shape[:2]
    base_x = w - 220
    base_y = img.shape[0] - 80 - len(lines) * 18
    _draw_panel(img, base_x - 8, base_y - 14, 224, len(lines) * 18 + 18)
    for i, (text, col) in enumerate(lines):
        _put(img, text, (base_x, base_y + i * 18), col, 0.45)


# ---------------------------------------------------------------------------
# Hardware initialisation
# ---------------------------------------------------------------------------

def _try_init(cls, name: str):
    try:
        obj = cls()
        log(f"{name} initialised.", level="info")
        return obj
    except Exception as e:
        log(f"{name} not available: {e}", level="warn")
        return None


def _read_sensors(pir, dht) -> dict:
    data = {}
    if pir:
        try:
            data["motion_detected"] = pir.motion_detected()
        except Exception:
            pass
    if dht:
        try:
            reading = dht.read()
            if reading.get("temperature") is not None:
                data["temperature"] = reading["temperature"]
            if reading.get("humidity") is not None:
                data["humidity"] = reading["humidity"]
        except Exception:
            pass
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("=== Manual Control Mode ===", level="info")

    # Init hardware
    log("Initialising servos...", level="info")
    sc   = ServoController()
    gait = GaitController(sc)

    log("Initialising vision...", level="info")
    vision = VisionDetector()

    log("Initialising display...", level="info")
    oled = OLEDDisplay()

    log("Initialising TTS...", level="info")
    tts = TextToSpeech()

    pir = _try_init(PIRSensor,   "PIR sensor")
    dht = _try_init(DHT11Sensor, "DHT11 sensor")

    # Starting mode
    mode          = "general"
    last_response = "—"
    last_action   = "stand"

    llm.reset_session(mode)
    sc.stand()
    oled.show("idle")
    tts.speak("Manual control active. General mode.")

    # Open camera window
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, 960, 720)
    log("Camera window open. Click it and use keyboard controls.", level="info")

    try:
        while True:
            # Always capture and display a fresh frame
            detections, frame = vision.detect_with_frame()
            sensor_data       = _read_sensors(pir, dht)

            # Draw overlays
            _draw_controls(frame)
            _draw_status(frame, mode, last_response, last_action)
            _draw_sensor_overlay(frame, sensor_data)

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(30) & 0xFF  # ~33 fps loop, non-blocking key read

            # ----------------------------------------------------------------
            # Movement keys
            # ----------------------------------------------------------------
            if key == ord('w'):
                log("Manual: walk_forward", level="info")
                last_action = "walk_forward"
                oled.show("searching")
                gait.execute("walk_forward")
                oled.show("idle")

            elif key == ord('a'):
                log("Manual: turn_left", level="info")
                last_action = "turn_left"
                oled.show("searching")
                gait.execute("turn_left")
                oled.show("idle")

            elif key == ord('d'):
                log("Manual: turn_right", level="info")
                last_action = "turn_right"
                oled.show("searching")
                gait.execute("turn_right")
                oled.show("idle")

            elif key == ord('s'):
                log("Manual: stand", level="info")
                last_action = "stand"
                sc.stand()
                oled.show("idle")

            # ----------------------------------------------------------------
            # Gemini query
            # ----------------------------------------------------------------
            elif key == ord(' '):
                log("Manual: querying Gemini...", level="info")
                oled.show("thinking")
                last_action = "ask Gemini"

                decision = llm.decide(
                    user_input   = "Describe what you currently see in one short sentence.",
                    detections   = detections,
                    mode         = mode,
                    sensor_data  = sensor_data,
                )

                text = decision.get("text", "")
                if not text:
                    # If Gemini returned a movement action instead of speak,
                    # ask it more directly as a follow-up
                    follow_up = llm.decide(
                        user_input  = "Just tell me what you see. Use the speak action.",
                        detections  = detections,
                        mode        = mode,
                        sensor_data = sensor_data,
                    )
                    text = follow_up.get("text", "I see: " + (
                        ", ".join(d["label"] for d in detections) or "nothing"
                    ))

                last_response = text
                tts.speak(text)
                oled.show("happy")
                log(f"Gemini response: {text}", level="info")

            # ----------------------------------------------------------------
            # Mode switching
            # ----------------------------------------------------------------
            elif key in MODE_KEYS:
                new_mode = MODE_KEYS[key]
                if new_mode != mode:
                    log(f"Mode switch: {mode} → {new_mode}", level="info")
                    mode        = new_mode
                    last_action = f"set mode: {new_mode}"
                    llm.reset_session(new_mode)
                    oled.show("thinking")
                    announce = f"Switching to {new_mode.replace('_', ' ')} mode."
                    last_response = announce
                    tts.speak(announce)
                    oled.show("idle")

            # ----------------------------------------------------------------
            # Face cycle
            # ----------------------------------------------------------------
            elif key == ord('f'):
                oled.show("happy")
                last_action = "face cycle"

            # ----------------------------------------------------------------
            # Quit
            # ----------------------------------------------------------------
            elif key in (ord('q'), 27):  # Q or ESC
                log("Quitting manual control.", level="info")
                break

    finally:
        sc.stand()
        oled.show("idle")
        vision.stop()
        cv2.destroyAllWindows()
        log("Manual control stopped.", level="info")


if __name__ == "__main__":
    main()
