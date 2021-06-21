import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
PIR_PIN = 17
GPIO.setup(PIR_PIN, GPIO.IN)



def MOTION(PIR_PIN):
    print("Motion detected!")

try:
    GPIO.add_event_detect(PIR_PIN, GPIO.FALLING, callback=MOTION)
    while 1:
        time.sleep(100)
except KeyboardInterrupt:
    GPIO.cleanup()
