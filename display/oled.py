import random
import threading
import time
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306, sh1106
from PIL import Image, ImageDraw
import config

from display.faces import (
    idle, idle_sleepy, idle_blink,
    thinking, thinking_sideways, thinking_up,
    searching, searching_alert,
    happy, happy_wink, happy_big, happy_star, excited,
    surprised, tongue_out,
)

# ---------------------------------------------------------------------------
# Face variant groups
# ---------------------------------------------------------------------------

FACE_GROUPS = {
    "idle":       [idle, idle_sleepy, idle_blink],
    "thinking":   [thinking, thinking_sideways, thinking_up],
    "searching":  [searching, searching_alert],
    "happy":      [happy, happy_wink, happy_big, happy_star, excited],
    "excited":    [excited],
    "surprised":  [surprised],
    "tongue_out": [tongue_out],
}

_last_shown: dict = {}

# ---------------------------------------------------------------------------
# Idle animation frames
# ---------------------------------------------------------------------------

_IDLE_OPEN = [
    (20, 18, 44, 42),
    (84, 18, 108, 42),
    (44, 52, 84, 56),
]
_IDLE_BLINK = [
    (20, 28, 44, 33),
    (84, 28, 108, 33),
    (44, 52, 84, 56),
]
_IDLE_HALF_BLINK = [
    (20, 24, 44, 36),
    (84, 24, 108, 36),
    (44, 52, 84, 56),
]
_IDLE_LOOK_LEFT = [
    (12, 18, 36, 42),
    (76, 18, 100, 42),
    (44, 52, 84, 56),
]
_IDLE_LOOK_RIGHT = [
    (28, 18, 52, 42),
    (92, 18, 116, 42),
    (44, 52, 84, 56),
]

_HAPPY_VARIANTS = [happy, happy_wink, happy_big, happy_star, excited, surprised]


class OLEDDisplay:
    def __init__(self):
        if config.MOCK_SERVOS:
            self.device = None
        else:
            serial = i2c(port=config.I2C_BUS, address=config.OLED_I2C_ADDRESS)
            self.device = sh1106(serial) if config.OLED_DRIVER == "sh1106" else ssd1306(serial)

        self._current_face = None
        self._anim_stop    = threading.Event()
        self._anim_thread  = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self, face: str):
        if face == self._current_face:
            return

        self._current_face = face
        self._stop_animation()

        if face == "idle":
            self._start_idle_animation()
        elif face == "happy":
            self._start_happy_animation()
        else:
            group   = FACE_GROUPS.get(face, FACE_GROUPS["happy"])
            last    = _last_shown.get(face)
            choices = [f for f in group if f is not last] if len(group) > 1 else group
            variant = random.choice(choices)
            _last_shown[face] = variant

            if config.MOCK_SERVOS:
                print(f"[MOCK] OLED face: {face} ({variant.__name__.split('.')[-1]})")
            else:
                self._render(variant.BITMAP)

    def show_text(self, text: str):
        self._stop_animation()
        self._current_face = None
        if config.MOCK_SERVOS:
            print(f"[MOCK] OLED text: {text}")
            return
        img  = Image.new("1", (config.OLED_WIDTH, config.OLED_HEIGHT))
        draw = ImageDraw.Draw(img)
        draw.text((4, 24), text, fill=1)
        self.device.display(img)

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------

    def _start_idle_animation(self):
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(target=self._idle_loop, daemon=True)
        self._anim_thread.start()

    def _start_happy_animation(self):
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(target=self._happy_loop, daemon=True)
        self._anim_thread.start()

    def _stop_animation(self):
        self._anim_stop.set()
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_thread.join(timeout=1)
        self._anim_thread = None

    def _idle_loop(self):
        while not self._anim_stop.is_set():
            wait = random.uniform(3.0, 5.0)
            if self._anim_stop.wait(timeout=wait):
                break
            if random.random() < 0.25:
                self._glance()
            else:
                self._blink()

    def _happy_loop(self):
        """Cycles through happy face variants every 1.5–3 seconds."""
        last = None
        while not self._anim_stop.is_set():
            choices = [f for f in _HAPPY_VARIANTS if f is not last]
            variant = random.choice(choices)
            last = variant
            if config.MOCK_SERVOS:
                print(f"[MOCK] OLED happy cycle: {variant.__name__.split('.')[-1]}")
            else:
                self._render(variant.BITMAP)
            if self._anim_stop.wait(timeout=random.uniform(1.5, 3.0)):
                break

    def _blink(self):
        if config.MOCK_SERVOS:
            return
        for bitmap in [_IDLE_HALF_BLINK, _IDLE_BLINK, _IDLE_HALF_BLINK, _IDLE_OPEN]:
            if self._anim_stop.is_set():
                return
            self._render(bitmap)
            time.sleep(0.07)

    def _glance(self):
        if config.MOCK_SERVOS:
            return
        direction = random.choice([_IDLE_LOOK_LEFT, _IDLE_LOOK_RIGHT])
        for bitmap in [direction, direction, _IDLE_OPEN]:
            if self._anim_stop.is_set():
                return
            self._render(bitmap)
            time.sleep(0.25)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self, bitmap: list):
        img  = Image.new("1", (config.OLED_WIDTH, config.OLED_HEIGHT))
        draw = ImageDraw.Draw(img)
        for shape in bitmap:
            draw.rectangle(shape, fill=1)
        self.device.display(img)
