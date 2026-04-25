import config


class DHT11Sensor:
    def __init__(self):
        if not config.MOCK_SERVOS:
            import adafruit_dht
            import board
            self.sensor = adafruit_dht.DHT11(
                getattr(board, f"D{config.DHT11_GPIO_PIN}")
            )
        else:
            self.sensor = None

    def read(self) -> dict:
        if config.MOCK_SERVOS:
            return {"temperature": None, "humidity": None}
        try:
            return {
                "temperature": self.sensor.temperature,
                "humidity":    self.sensor.humidity
            }
        except RuntimeError:
            return {"temperature": None, "humidity": None}
