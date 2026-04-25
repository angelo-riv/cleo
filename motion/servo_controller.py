import config


class _MockServoController:
    """No-op servo controller — prints commands instead of touching hardware."""

    def set_angle(self, joint_name: str, angle: float):
        print(f"[MOCK] {joint_name} → {angle:.1f}°")

    def set_pose(self, pose: dict):
        for joint, angle in pose.items():
            self.set_angle(joint, angle)

    def stand(self):
        print("[MOCK] stand()")
        self.set_pose(config.STAND_POSE)

    def relax(self):
        print("[MOCK] relax()")


class _RealServoController:
    def __init__(self):
        import board
        import busio
        from adafruit_pca9685 import PCA9685
        from adafruit_motor import servo

        i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(i2c, address=config.PCA9685_ADDRESS)
        self.pca.frequency = config.PWM_FREQUENCY
        self.servos = {
            name: servo.Servo(self.pca.channels[ch],
                              min_pulse=500, max_pulse=2500)
            for name, ch in config.SERVO_CHANNELS.items()
        }

    def set_angle(self, joint_name: str, angle: float):
        angle = max(config.SERVO_MIN_ANGLE,
                    min(config.SERVO_MAX_ANGLE, angle))
        self.servos[joint_name].angle = angle

    def set_pose(self, pose: dict):
        for joint, angle in pose.items():
            self.set_angle(joint, angle)

    def stand(self):
        self.set_pose(config.STAND_POSE)

    def relax(self):
        for s in self.servos.values():
            s.angle = None  # de-energize all servos


def ServoController():
    if config.MOCK_SERVOS:
        return _MockServoController()
    return _RealServoController()
