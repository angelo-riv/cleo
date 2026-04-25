import config


class ModuleDetector:
    def __init__(self):
        if not config.MOCK_SERVOS:
            import board
            import busio
            self.i2c = busio.I2C(board.SCL, board.SDA)
        else:
            self.i2c = None

    def detect(self) -> str:
        """
        Scan I2C bus and return module mode string.
        Returns 'environment', 'security', or 'general'.
        """
        if config.MOCK_SERVOS:
            print("[MOCK] Module scan skipped — defaulting to general mode")
            return "general"

        try:
            while not self.i2c.try_lock():
                pass
            addresses = self.i2c.scan()
        finally:
            self.i2c.unlock()

        for addr in addresses:
            if addr in config.MODULE_I2C_ADDRESSES:
                mode = config.MODULE_I2C_ADDRESSES[addr]
                print(f"Module detected: {mode} (0x{addr:02X})")
                return mode

        print("No I2C module found — defaulting to general mode")
        return "general"
