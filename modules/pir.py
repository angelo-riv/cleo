import config


class PIRSensor:
    def __init__(self):
        if not config.MOCK_SERVOS:
            import RPi.GPIO as GPIO
            self._GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.PIR_GPIO_PIN, GPIO.IN)
        else:
            self._GPIO = None

    def motion_detected(self) -> bool:
        if config.MOCK_SERVOS:
            return False
        return self._GPIO.input(config.PIR_GPIO_PIN) == self._GPIO.HIGH

    def cleanup(self):
        if not config.MOCK_SERVOS:
            self._GPIO.cleanup()
