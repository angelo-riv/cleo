import time
import config


class Animations:
    def __init__(self, servo_controller):
        self.sc = servo_controller

    # ------------------------------------------------------------------
    # Wave — lifts the front right paw and swings it side to side
    # ------------------------------------------------------------------

    def wave(self):
        sc = self.sc
        sp = config.STAND_POSE

        # Shift weight forward so rear right leg is free
        sc.set_angle("front_right_hip", sp["front_right_hip"] - 10)
        sc.set_angle("front_left_hip",  sp["front_left_hip"]  + 10)
        time.sleep(0.4)

        # Wave R4 up and down 4 times
        # R4: 30=down, 180=up
        lo, hi = config.SERVO_LIMITS["rear_right_knee"]
        wave_up   = min(hi, sp["rear_right_knee"] + 50)
        wave_down = max(lo, sp["rear_right_knee"] - 40)
        for _ in range(4):
            sc.set_angle("rear_right_knee", wave_up)
            time.sleep(0.25)
            sc.set_angle("rear_right_knee", wave_down)
            time.sleep(0.25)

        # Return to stand
        sc.set_angle("rear_right_knee", sp["rear_right_knee"])
        sc.set_angle("front_right_hip", sp["front_right_hip"])
        sc.set_angle("front_left_hip",  sp["front_left_hip"])
        time.sleep(0.4)

    # ------------------------------------------------------------------
    # Dance — bounce, hip shake, and a little spin
    # ------------------------------------------------------------------

    def dance(self):
        sc = self.sc
        sp = config.STAND_POSE

        # --- Bounce x3 ---
        # Rear knees control body height: R4 up=180, L4 up=0
        r4_lo, r4_hi = config.SERVO_LIMITS["rear_right_knee"]
        l4_lo, l4_hi = config.SERVO_LIMITS["rear_left_knee"]
        squat_r4 = max(r4_lo, sp["rear_right_knee"] - 30)
        squat_l4 = min(l4_hi, sp["rear_left_knee"]  + 30)
        rise_r4  = min(r4_hi, sp["rear_right_knee"] + 30)
        rise_l4  = max(l4_lo, sp["rear_left_knee"]  - 30)

        for _ in range(3):
            sc.set_angle("rear_right_knee", squat_r4)
            sc.set_angle("rear_left_knee",  squat_l4)
            time.sleep(0.2)
            sc.set_angle("rear_right_knee", rise_r4)
            sc.set_angle("rear_left_knee",  rise_l4)
            time.sleep(0.2)

        sc.stand()
        time.sleep(0.3)

        # --- Hip shake x3 — left hips forward, right hips back, then swap ---
        fl_lo, fl_hi = config.SERVO_LIMITS["front_left_hip"]
        rl_lo, rl_hi = config.SERVO_LIMITS["rear_left_hip"]
        fr_lo, fr_hi = config.SERVO_LIMITS["front_right_hip"]

        shake = 25
        fl_fwd  = min(fl_hi, sp["front_left_hip"]  + shake)
        rl_fwd  = min(rl_hi, sp["rear_left_hip"]   + shake)
        fr_fwd  = min(fr_hi, sp["front_right_hip"] + shake)
        fl_back = max(fl_lo, sp["front_left_hip"]  - shake)
        rl_back = max(rl_lo, sp["rear_left_hip"]   - shake)
        fr_back = max(fr_lo, sp["front_right_hip"] - shake)

        for _ in range(3):
            # Left side forward, right side back
            sc.set_angle("front_left_hip",  fl_fwd)
            sc.set_angle("rear_left_hip",   rl_fwd)
            sc.set_angle("front_right_hip", fr_back)
            time.sleep(0.2)
            # Left side back, right side forward
            sc.set_angle("front_left_hip",  fl_back)
            sc.set_angle("rear_left_hip",   rl_back)
            sc.set_angle("front_right_hip", fr_fwd)
            time.sleep(0.2)

        sc.stand()
        time.sleep(0.3)

        # --- Spin — two quick turns ---
        from motion.gait import GaitController
        gc = GaitController(sc)
        gc.turn_left()
        gc.turn_left()

        sc.stand()
