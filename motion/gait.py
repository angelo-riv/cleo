import time
import copy
import config
from motion.servo_controller import ServoController

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

    def _move_leg(self, leg: str, direction: str):
        hip  = f"{leg}_hip"
        knee = f"{leg}_knee"
        base_hip  = config.STAND_POSE[hip]
        base_knee = config.STAND_POSE[knee]
        step  = config.GAIT_STEP_ANGLE
        lift  = config.GAIT_LIFT_ANGLE
        delay = config.GAIT_STEP_DELAY

        # lift
        self.sc.set_angle(knee, base_knee + lift)
        time.sleep(delay)

        # swing
        offset = step if direction == "forward" else -step
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
