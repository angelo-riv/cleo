import cv2
from motion.servo_controller import ServoController
from motion.gait import GaitController
from vision.detector import VisionDetector
from display.oled import OLEDDisplay
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from modules.detector import ModuleDetector
from modules.pir import PIRSensor
from modules.dht11 import DHT11Sensor
from brain import llm
from utils.logger import log
import config
import time


class Agent:
    def __init__(self):
        log("Initialising servos...", level="info")
        self.sc   = ServoController()
        self.gait = GaitController(self.sc)

        log("Initialising vision...", level="info")
        self.vision = VisionDetector()

        log("Initialising display...", level="info")
        self.oled = OLEDDisplay()

        log("Initialising voice...", level="info")
        self.stt = SpeechToText()
        self.tts = TextToSpeech()

        log("Detecting module...", level="info")
        self.module = ModuleDetector()

        # Sensors are optional — gracefully skip if hardware is absent
        self.pir = self._try_init(PIRSensor,   "PIR sensor")
        self.dht = self._try_init(DHT11Sensor, "DHT11 sensor")

        if config.SHOW_CAMERA_FEED:
            cv2.namedWindow(config.CAMERA_WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(config.CAMERA_WINDOW_NAME, 960, 720)
            log("Camera feed window opened.", level="info")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _try_init(cls, name: str):
        try:
            instance = cls()
            log(f"{name} initialised.", level="info")
            return instance
        except Exception as e:
            log(f"{name} not available: {e}", level="warn")
            return None

    def _detect(self) -> list:
        """
        Capture a frame, run detection, and optionally show the annotated feed.
        Returns the detection results list.
        """
        if config.SHOW_CAMERA_FEED:
            detections, frame = self.vision.detect_with_frame()
            try:
                cv2.imshow(config.CAMERA_WINDOW_NAME, frame)
                cv2.waitKey(1)  # non-blocking — just refreshes the window
            except Exception:
                pass  # if display is unavailable, don't crash the agent
            return detections
        else:
            return self.vision.detect()

    def _read_sensors(self) -> dict:
        """Collect live readings from any attached sensor modules."""
        data = {}
        if self.pir:
            try:
                data["motion_detected"] = self.pir.motion_detected()
            except Exception:
                pass
        if self.dht:
            try:
                reading = self.dht.read()
                if reading.get("temperature") is not None:
                    data["temperature"] = reading["temperature"]
                if reading.get("humidity") is not None:
                    data["humidity"] = reading["humidity"]
            except Exception:
                pass
        return data

    def _handle_speak(self, decision: dict):
        text = decision.get("text", "")
        if text:
            self.tts.speak(text)

    def _handle_set_mode(self, decision: dict, current_mode: str) -> str:
        """Switch robot mode. Returns the new mode string."""
        new_mode = decision.get("mode", current_mode)
        if new_mode not in ("general", "security", "environment", "search_rescue"):
            log(f"Unknown mode '{new_mode}' — staying in {current_mode}", level="warn")
            return current_mode
        self._handle_speak(decision)
        llm.reset_session(new_mode)
        log(f"Mode switched: {current_mode} → {new_mode}", level="info")
        return new_mode

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.sc.stand()
        self.oled.show("idle")
        mode = self.module.detect()
        llm.reset_session(mode)
        mode_label = mode.replace("_", " ")
        self.tts.speak(f"Hey! I'm Cleo. {mode_label} mode active. Let's go!")

        prompted = False
        last_idle_motion = time.monotonic()

        while True:
            self.oled.show("idle")

            if not prompted:
                self.tts.speak("I'm listening.")
                prompted = True

            user_input = self.stt.listen(duration=5)

            if not user_input:
                # Keep the camera feed alive even while waiting for speech
                if config.SHOW_CAMERA_FEED:
                    self._detect()

                # Run a subtle idle animation every N seconds while waiting.
                interval = getattr(config, "IDLE_ANIMATION_INTERVAL", 30.0)
                if getattr(config, "IDLE_ANIMATION_ENABLED", True):
                    now = time.monotonic()
                    if (now - last_idle_motion) >= interval:
                        try:
                            self.gait.idle()
                        except Exception as e:
                            log(f"Idle animation failed: {e}", level="warn")
                        last_idle_motion = now
                continue

            self.oled.show("thinking")
            detections  = self._detect()
            sensor_data = self._read_sensors()
            decision    = llm.decide(user_input, detections, mode, sensor_data)
            action      = decision.get("action", "stop")

            log(f"Top-level action: {action}", level="info")

            if action == "speak":
                self._handle_speak(decision)
                prompted = False

            elif action == "set_mode":
                mode     = self._handle_set_mode(decision, mode)
                prompted = False

            elif action == "complete":
                self.oled.show("happy")
                self.tts.speak("Already done! Easy.")
                self.sc.stand()
                prompted = False

            elif action == "stop":
                self.sc.stand()
                prompted = False

            else:
                self.tts.speak("On it!")
                mode = self._run_mission(
                    mission      = user_input,
                    mode         = mode,
                    first_action = action,
                )
                prompted = False

    # ------------------------------------------------------------------
    # Mission execution
    # ------------------------------------------------------------------

    def _run_mission(self, mission: str, mode: str, first_action: str) -> str:
        """
        Execute a physical mission until complete, max steps reached, or mode switch.
        Returns the current mode (may have changed mid-mission via set_mode).
        """
        self.oled.show("searching")
        max_steps = 30

        self.gait.execute(first_action)

        for step in range(max_steps - 1):
            self.oled.show("thinking")
            detections  = self._detect()
            sensor_data = self._read_sensors()
            decision    = llm.decide(mission, detections, mode, sensor_data)
            action      = decision.get("action", "stop")

            log(
                f"Step {step + 2}/{max_steps}: {action} | "
                f"Seen: {[d['label'] for d in detections]}",
                level="info",
            )

            if action == "complete":
                self.oled.show("happy")
                self.tts.speak("Mission complete.")
                self.sc.stand()
                return mode

            elif action == "speak":
                self._handle_speak(decision)
                self.oled.show("searching")

            elif action == "set_mode":
                mode = self._handle_set_mode(decision, mode)
                self.sc.stand()
                return mode

            elif action == "stop":
                self.sc.stand()
                self.oled.show("idle")
                return mode

            else:
                self.oled.show("searching")
                self.gait.execute(action)

        self.tts.speak("Hmm, I couldn't finish that one. Sorry!")
        self.sc.stand()
        self.oled.show("idle")
        return mode
