import cv2
import os
import sys
import termios
import tty
import threading
import time
import random
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
from motion.animations import Animations
from utils.logger import log
import config


class Agent:
    def __init__(self):
        self._interrupt = threading.Event()
        self._demo_mode = False
        self._start_key_listener()

        log("Initialising servos...", level="info")
        self.sc   = ServoController()
        self.gait = GaitController(self.sc)
        self.anim = Animations(self.sc)

        log("Initialising vision...", level="info")
        self.vision = VisionDetector()

        # Shared camera state — written by capture thread, read by display + detect
        self._raw_frame     = None
        self._frame_lock    = threading.Lock()
        self._last_dets     = []
        self._det_lock      = threading.Lock()

        self._start_capture_thread()
        self._display_ok = self._check_display()
        if self._display_ok:
            log("Camera feed window starting.", level="info")
        else:
            log("No display detected — camera feed disabled.", level="info")

        log("Initialising display...", level="info")
        self.oled = OLEDDisplay()

        log("Initialising voice...", level="info")
        self.stt = SpeechToText()
        self.tts = TextToSpeech()

        log("Detecting module...", level="info")
        self.module = ModuleDetector()

        self.pir = self._try_init(PIRSensor,   "PIR sensor")
        self.dht = self._try_init(DHT11Sensor, "DHT11 sensor")

    # ------------------------------------------------------------------
    # Camera threads
    # ------------------------------------------------------------------

    def _check_display(self) -> bool:
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False
        try:
            cv2.namedWindow("_probe", cv2.WINDOW_NORMAL)
            cv2.destroyWindow("_probe")
            return True
        except Exception:
            return False

    def _start_capture_thread(self):
        def _capture():
            while True:
                ok, frame = self.vision.cam.read()
                if ok:
                    with self._frame_lock:
                        self._raw_frame = frame
                else:
                    time.sleep(0.01)

        t = threading.Thread(target=_capture, daemon=True)
        t.start()

    def _display_main_loop(self):
        """Runs on the main thread — OpenCV GUI requires this on Linux/GTK."""
        cv2.namedWindow(config.CAMERA_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(config.CAMERA_WINDOW_NAME, 960, 720)
        while True:
            with self._frame_lock:
                frame = self._raw_frame
            if frame is not None:
                with self._det_lock:
                    dets = list(self._last_dets)
                annotated = self.vision.annotate(frame, dets)
                cv2.imshow(config.CAMERA_WINDOW_NAME, annotated)
            cv2.waitKey(1)
            time.sleep(0.033)  # ~30 fps

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _start_key_listener(self):
        def _listen():
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch == ' ':
                        self._interrupt.set()
                        log("Interrupt! Stopping current action.", level="info")
                    elif ch == 'q':
                        self._demo_mode = not self._demo_mode
                        state = "ON" if self._demo_mode else "OFF"
                        log(f"Demo mode {state} — listening {'paused' if self._demo_mode else 'resumed'}.", level="info")
            except Exception:
                pass
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        t = threading.Thread(target=_listen, daemon=True)
        t.start()

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
        with self._frame_lock:
            frame = self._raw_frame
        if frame is None:
            return []
        detections = self.vision._run_detection(frame)
        with self._det_lock:
            self._last_dets = detections
        return detections

    def _read_sensors(self) -> dict:
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

    _SPEAK_FACES = ["happy", "excited", "surprised", "happy", "excited"]

    def _handle_speak(self, decision: dict):
        text = decision.get("text", "")
        if not text:
            return
        stop_cycling = threading.Event()
        def _cycle():
            while not stop_cycling.wait(timeout=random.uniform(0.7, 1.3)):
                self.oled.show(random.choice(self._SPEAK_FACES))
        t = threading.Thread(target=_cycle, daemon=True)
        t.start()
        self.tts.speak(text)
        stop_cycling.set()
        t.join(timeout=0.5)

    def _handle_set_mode(self, decision: dict, current_mode: str) -> str:
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
        t = threading.Thread(target=self._run_logic, daemon=True)
        t.start()
        if self._display_ok:
            self._display_main_loop()  # blocks main thread — OpenCV needs it
        else:
            t.join()

    def _run_logic(self):
        self.sc.stand()
        self.oled.show("idle")
        mode = self.module.detect()
        llm.reset_session(mode)
        mode_label = mode.replace("_", " ")
        self.tts.speak(f"Hey! I'm Cleo. {mode_label} mode active. Let's go!")

        last_activity  = time.time()
        demo_last_tick = time.time()

        while True:
            self._interrupt.clear()

            if self._demo_mode:
                self.oled.show("happy")
                time.sleep(1)
                if time.time() - demo_last_tick >= config.IDLE_DANCE_TIMEOUT:
                    self._demo_tick()
                    demo_last_tick = time.time()
                last_activity = time.time()
                continue

            self.oled.show("happy")
            user_input = self.stt.listen(duration=5)

            if not user_input:
                if time.time() - last_activity >= config.IDLE_DANCE_TIMEOUT:
                    self.oled.show("tongue_out")
                    self.anim.dance()
                    self.oled.show("happy")
                    self.sc.stand()
                    last_activity = time.time()
                continue

            self.oled.show("thinking")
            detections  = self._detect()
            sensor_data = self._read_sensors()
            decision    = llm.decide(user_input, detections, mode, sensor_data)
            action      = decision.get("action", "stop")

            log(f"Top-level action: {action}", level="info")
            last_activity = time.time()

            if action == "speak":
                self._handle_speak(decision)

            elif action == "set_mode":
                mode = self._handle_set_mode(decision, mode)

            elif action == "complete":
                self.oled.show("happy")
                self.tts.speak("Already done! Easy.")
                self.sc.stand()

            elif action == "stop":
                self.sc.stand()

            elif action == "wave":
                self.oled.show("happy")
                self.anim.wave()
                self.sc.stand()

            elif action == "dance":
                self.oled.show("tongue_out")
                self.anim.dance()
                self.oled.show("happy")
                self.sc.stand()

            else:
                self.tts.speak("On it!")
                mode = self._run_mission(
                    mission      = user_input,
                    mode         = mode,
                    first_action = action,
                )

    # ------------------------------------------------------------------
    # Mission execution
    # ------------------------------------------------------------------

    _LOOK_FACES = ["searching", "searching_alert", "thinking_sideways", "thinking_up", "surprised"]

    def _demo_tick(self):
        for face in random.sample(self._LOOK_FACES, 3):
            self.oled.show(face)
            time.sleep(0.6)
        if random.random() < 0.5:
            self.oled.show("tongue_out")
            self.anim.dance()
        else:
            self.oled.show("happy")
            self.anim.wave()
        self.sc.stand()
        self.tts.speak(random.choice([
            "Hey, anybody there?",
            "Hello? Anyone around?",
            "Come talk to me!",
        ]))
        self.oled.show("happy")

    def _interrupted(self) -> bool:
        if self._interrupt.is_set():
            self._interrupt.clear()
            return True
        return False

    def _run_mission(self, mission: str, mode: str, first_action: str) -> str:
        self.oled.show("searching")
        max_steps = config.MISSION_MAX_STEPS

        if self._interrupted():
            self.sc.stand()
            return mode

        self.gait.execute(first_action)

        for step in range(max_steps - 1):
            if self._interrupted():
                log("Mission interrupted by spacebar.", level="info")
                self.sc.stand()
                self.oled.show("happy")
                return mode

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
                self.oled.show("happy")
                return mode

            else:
                self.oled.show("searching")
                self.gait.execute(action)

        self.tts.speak("Hmm, I couldn't finish that one. Sorry!")
        self.sc.stand()
        self.oled.show("happy")
        return mode
