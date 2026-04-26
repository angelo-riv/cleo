import time
import copy
import config
from motion.servo_controller import ServoController
import random

# Creep gait leg order — one leg moves at a time
LEG_SEQUENCE = [
    "front_left",
    "rear_right",
    "front_right",
    "rear_left",
]


class GaitController:
    def __init__(self, servo_controller: ServoController):
        self.sc = servo_controller
        self.current_pose = copy.deepcopy(config.STAND_POSE)

    def idle(self):
        """
        Subtle idle animation to keep the robot feeling "alive".
        Designed to be safe: small angles, one leg at a time, always returns to stand.
        """
        if not getattr(config, "IDLE_ANIMATION_ENABLED", True):
            return

        base = config.STAND_POSE
        hip_sway = getattr(config, "IDLE_HIP_SWAY_ANGLE", 8)
        knee_lift = getattr(config, "IDLE_KNEE_LIFT_ANGLE", 12)
        delay = getattr(config, "IDLE_STEP_DELAY", config.GAIT_STEP_DELAY)

        # Pick a leg to "stretch" to avoid looking repetitive.
        leg = random.choice(["front_left", "front_right", "rear_left", "rear_right"])
        hip = f"{leg}_hip"
        knee = f"{leg}_knee"

        # Mirror-aware hip sway: left/right hips are mounted mirrored in the gait code.
        is_left = "left" in leg
        sway = hip_sway if is_left else -hip_sway

        # Knee lift direction depends on servo mounting (same logic as _move_leg).
        is_rear = leg.startswith("rear")
        flip_knee = (is_left and is_rear) or (not is_left and not is_rear)
        lift = -knee_lift if flip_knee else knee_lift

        # Lift knee a little.
        self.sc.set_angle(knee, base[knee] + lift)
        time.sleep(delay)

        # Small hip sway while lifted.
        self.sc.set_angle(hip, base[hip] + sway)
        time.sleep(delay)

        # Return hip, then plant knee.
        self.sc.set_angle(hip, base[hip])
        time.sleep(delay)
        self.sc.set_angle(knee, base[knee])
        time.sleep(delay)

    def _move_leg(self, leg: str, direction: str):
        hip  = f"{leg}_hip"
        knee = f"{leg}_knee"
        base_hip  = config.STAND_POSE[hip]
        base_knee = config.STAND_POSE[knee]
        step  = config.GAIT_STEP_ANGLE
        lift  = config.GAIT_LIFT_ANGLE
        delay = config.GAIT_STEP_DELAY

        # Left and right hips are mirrored
        is_left = "left" in leg
        is_rear  = leg.startswith("rear")
        offset = step if (is_left == (direction == "forward")) else -step

        # Each knee has its own lift direction based on how the servo is mounted
        # +lift: front_left (L2), rear_right (R4)
        # -lift: front_right (R2), rear_left (L4)
        flip_knee = (is_left and is_rear) or (not is_left and not is_rear)
        knee_lift = -lift if flip_knee else lift

        # lift
        self.sc.set_angle(knee, base_knee + knee_lift)
        time.sleep(delay)

        # swing
        self.sc.set_angle(hip, base_hip + offset)
        time.sleep(delay)

        # plant
        self.sc.set_angle(knee, base_knee)
        time.sleep(delay)

        # return hip to neutral
        self.sc.set_angle(hip, base_hip)
        time.sleep(delay)

    def step_forward(self):
        for leg in LEG_SEQUENCE:
            self._move_leg(leg, "forward")

    def turn_left(self):
        for leg in ["front_left", "rear_left"]:
            self._move_leg(leg, "backward")
        for leg in ["front_right", "rear_right"]:
            self._move_leg(leg, "forward")

    def turn_right(self):
        for leg in ["front_right", "rear_right"]:
            self._move_leg(leg, "backward")
        for leg in ["front_left", "rear_left"]:
            self._move_leg(leg, "forward")

    def execute(self, action: str):
        if action == "walk_forward":
            self.step_forward()
        elif action == "turn_left":
            self.turn_left()
        elif action == "turn_right":
            self.turn_right()
        elif action == "stop":
            self.sc.stand()
