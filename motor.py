
import time
import RPi.GPIO as GPIO

class ServoMotor:
    def __init__(self, pin=4):
        # GPIOの初期設定
        GPIO.setmode(GPIO.BCM)

        # GPIOを出力端子設定
        GPIO.setup(pin, GPIO.OUT)

        # GPIOをPWM設定、周波数は50Hz
        self.p = GPIO.PWM(pin, 50)

    def move_to_position(self, degree):
        # Duty Cycle 0%
        self.p.start(0.0)

        # -90°の位置へ移動
        self.p.ChangeDutyCycle(2.5)
        time.sleep(1.0)

        # 少しずつ回転
        for d in range(-90, degree + 1):
            dc = 2.5 + (12.0 - 2.5) / 180 * (d + 90)
            self.p.ChangeDutyCycle(dc)
            time.sleep(0.03)
            self.p.ChangeDutyCycle(0.0)  # 一旦DutyCycle 0%にする


#motor = ServoMotor()
#while True:
#	m = input('motor')
#	if m == 'motor':
#		motor.move_to_position(30)
