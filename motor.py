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
        self.p.start(2.5)

        # サーボモータを指定の角度に移動するための処理
        duty_cycle = ((degree - 0) * (12.5 - 2.5) / (180 - 0)) + 2.5
        self.p.ChangeDutyCycle(duty_cycle)
        time.sleep(1.0)
        
        # 元の位置（0度）に戻す
        self.p.ChangeDutyCycle(2.5)
        time.sleep(1.0)

motor = ServoMotor()
motor.move_to_position(90)

