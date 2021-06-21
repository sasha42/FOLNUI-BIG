# coding: utf-8
import time
import RPi.GPIO as GPIO
from devices import timeout, loadLEDs 

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define GPIO to use on Pi
GPIO_TRIGECHO = 15

print("Ultrasonic Measurement")

# Set pins as output and input
GPIO.setup(GPIO_TRIGECHO,GPIO.OUT)  # Initial state as output


# Set trigger to False (Low)
GPIO.output(GPIO_TRIGECHO, False)

def measure():
  # This function measures a distance
  # Pulse the trigger/echo line to initiate a measurement
    GPIO.output(GPIO_TRIGECHO, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGECHO, False)
  #ensure start time is set in case of very quick return
    start = time.time()

  # set line to input to check for start of echo response
    GPIO.setup(GPIO_TRIGECHO, GPIO.IN)
    while GPIO.input(GPIO_TRIGECHO)==0:
        start = time.time()

  # Wait for end of echo response
    while GPIO.input(GPIO_TRIGECHO)==1:
        stop = time.time()
  
    GPIO.setup(GPIO_TRIGECHO, GPIO.OUT)
    GPIO.output(GPIO_TRIGECHO, False)

    elapsed = stop-start
    distance = (elapsed * 34300)/2.0
    time.sleep(0.1)
    return distance


def changeLights(distance, bulbs):
    """Change lights based on distance"""

    max_distance = 268.4
    min_distance = 50.5

    dist_range = max_distance-min_distance
    
    est_height = round(abs(max_distance-distance), 2)

    norm_distance = distance-min_distance
    percentage = (1-(norm_distance/max_distance))

    brightness = 255*percentage
    #print(brightness)
    
    if brightness < 100:
        brightness = 1

    if brightness > 100:
        brightness = 255

    for bulb in bulbs:
        with timeout(1):
            bulbs[bulb].setRgb(brightness, brightness, brightness)

try:
    # set up the LEDs
    with timeout(1): # 10 s timeout
        bulbs = loadLEDs()

    if len(bulbs) == 0:
        printLog("No lights connected!")
        raise RuntimeError

    while True:

        distance = measure()
        #print("Distance : %.1f cm" % distance)
        changeLights(distance, bulbs)
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Stop")
    GPIO.cleanup()
