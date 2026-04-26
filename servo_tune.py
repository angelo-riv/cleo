import board, busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo as servo_lib

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c, address=0x40)
pca.frequency = 50

channels = [
    ('front_right_hip  (R1)', 0),
    ('front_right_knee (R2)', 11),
    ('front_left_hip   (L1)', 2),
    ('front_left_knee  (L2)', 3),
    ('rear_right_knee  (R4)', 4),
    ('rear_right_hip   (R3)', 12),
    ('rear_left_hip    (L3)', 9),
    ('rear_left_knee   (L4)', 7),
]

print('Servo tuner — enter angles to test, "n" for next servo, "q" to quit')

for name, ch in channels:
    print(f'\n--- Channel {ch}: {name} ---')
    s = servo_lib.Servo(pca.channels[ch], min_pulse=500, max_pulse=2500)
    angle = 90
    s.angle = angle
    print('Starting at 90. Enter angle (0-180) or "n" for next:')
    while True:
        val = input(f'  angle [{angle}]: ').strip()
        if val == 'q':
            pca.deinit()
            exit()
        if val == 'n':
            s.angle = None
            break
        try:
            angle = max(0, min(180, int(val)))
            s.angle = angle
        except ValueError:
            pass

pca.deinit()
print('Done')
