
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
        self.p.ChangeDutyCycle(9.0)
        time.sleep(1.0)
        #-90°の位置へ移動
        self.p.ChangeDutyCycle(2.5)

"""
motor = ServoMotor()
print('move')
motor.move_to_position(30)
print('move end')
"""
