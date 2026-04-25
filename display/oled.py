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
    surprised,
)

# ---------------------------------------------------------------------------
# Face variant groups
# ---------------------------------------------------------------------------

FACE_GROUPS = {
    "idle":      [idle, idle_sleepy, idle_blink],
    "thinking":  [thinking, thinking_sideways, thinking_up],
    "searching": [searching, searching_alert],
    "happy":     [happy, happy_wink, happy_big, happy_star, excited],
    "surprised": [surprised],
}

_last_shown: dict = {}

# ---------------------------------------------------------------------------
# Idle animation frames
# Eyes shifted left, right, and centre for glancing
# ---------------------------------------------------------------------------

_IDLE_OPEN = [
    (20, 18, 44, 42),   # left eye
    (84, 18, 108, 42),  # right eye
    (44, 52, 84, 56),   # mouth
]
_IDLE_BLINK = [
    (20, 28, 44, 33),   # left eye slit
    (84, 28, 108, 33),  # right eye slit
    (44, 52, 84, 56),
]
_IDLE_HALF_BLINK = [
    (20, 24, 44, 36),   # left eye half
    (84, 24, 108, 36),  # right eye half
    (44, 52, 84, 56),
]
_IDLE_LOOK_LEFT = [
    (12, 18, 36, 42),   # left eye shifted left
    (76, 18, 100, 42),  # right eye shifted left
    (44, 52, 84, 56),
]
_IDLE_LOOK_RIGHT = [
    (28, 18, 52, 42),   # left eye shifted right
    (92, 18, 116, 42),  # right eye shifted right
    (44, 52, 84, 56),
]


class OLEDDisplay:
    def __init__(self):
        if config.MOCK_SERVOS:
            self.device = None
        else:
            serial = i2c(port=config.I2C_BUS, address=config.OLED_I2C_ADDRESS)
            self.device = sh1106(serial) if config.OLED_DRIVER == "sh1106" else ssd1306(serial)

        self._current_face  = None
        self._anim_stop     = threading.Event()
        self._anim_thread   = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self, face: str):
        """
        Display a face state. If face is 'idle', starts the live idle
        animation (blinking + glancing). Any other state stops the animation
        and shows a static face variant.
        """
        if face == self._current_face:
            return  # already showing this — no flicker

        self._current_face = face
        self._stop_animation()

        if face == "idle":
            self._start_idle_animation()
        else:
            group   = FACE_GROUPS.get(face, FACE_GROUPS["idle"])
            last    = _last_shown.get(face)
            choices = [f for f in group if f is not last] if len(group) > 1 else group
            variant = random.choice(choices)
            _last_shown[face] = variant

            if config.MOCK_SERVOS:
                print(f"[MOCK] OLED face: {face} ({variant.__name__.split('.')[-1]})")
            else:
                self._render(variant.BITMAP)

    def show_text(self, text: str):
        """Display a short text string instead of a face."""
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
    # Idle animation
    # ------------------------------------------------------------------

    def _start_idle_animation(self):
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(target=self._idle_loop, daemon=True)
        self._anim_thread.start()

    def _stop_animation(self):
        self._anim_stop.set()
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_thread.join(timeout=1)
        self._anim_thread = None

    def _idle_loop(self):
        """
        Runs in a background thread while face == 'idle'.
        Randomly blinks every 3-5 seconds and occasionally glances left or right.
        """
        while not self._anim_stop.is_set():
            # Hold open eyes for 3–5 seconds
            wait = random.uniform(3.0, 5.0)
            if self._anim_stop.wait(timeout=wait):
                break

            # Occasionally glance instead of blink (25% chance)
            if random.random() < 0.25:
                self._glance()
            else:
                self._blink()

        # Clear display when done (other face will redraw)

    def _blink(self):
        """Quick 3-frame blink: open → half → closed → half → open."""
        if config.MOCK_SERVOS:
            return
        for bitmap in [_IDLE_HALF_BLINK, _IDLE_BLINK, _IDLE_HALF_BLINK, _IDLE_OPEN]:
            if self._anim_stop.is_set():
                return
            self._render(bitmap)
            time.sleep(0.07)

    def _glance(self):
        """Eyes shift left or right then return to centre."""
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
