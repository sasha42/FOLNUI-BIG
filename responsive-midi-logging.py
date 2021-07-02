# coding: utf-8
import time
import RPi.GPIO as GPIO
import mido
import logging
from rlog import RedisHandler
import sys
from timeout import timeout

# Use redis for logs
logger = logging.getLogger()
logger.addHandler(RedisHandler(channel='logs'))
logger.setLevel(logging.DEBUG)

# Log stdout stuff
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s: %(message)s', "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Use global state for whether someone is detected under sensor
#detected = False

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define GPIO to use on Pi
#GPIO_TRIGECHO = 4
#GPIO_PINS = [4, 17, 18, 27, 22, 23, 25]
sensors = [4, 17, 18]

logger.info("Ultrasonic Measurement")

def setupSensor(gpioPin):
    """Sets up a sensor by configuring the GPIO parameters for it"""
    # Set pins as output and input
    GPIO.setup(gpioPin,GPIO.OUT)  # Initial state as output

    # Set trigger to False (Low)
    GPIO.output(gpioPin, False)


def measureSensor(gpioPin):
    """Measures the distnace of an individual sensor"""
    # Pulse the trigger/echo line to initiate a measurement
    GPIO.output(gpioPin, True)
    time.sleep(0.00001)
    GPIO.output(gpioPin, False)

    #ensure start time is set in case of very quick return
    start = time.time()

    # set line to input to check for start of echo response
    GPIO.setup(gpioPin, GPIO.IN)
    while GPIO.input(gpioPin)==0:
        start = time.time()

    # Wait for end of echo response
    while GPIO.input(gpioPin)==1:
        stop = time.time()
  
    GPIO.setup(gpioPin, GPIO.OUT)
    GPIO.output(gpioPin, False)

    elapsed = stop-start
    distance = (elapsed * 34300)/2.0
    return distance


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

    global detected

    max_distance = 268.4
    min_distance = 50.5

    dist_range = max_distance-min_distance
    
    est_height = round(abs(max_distance-distance), 2)

    norm_distance = distance-min_distance
    percentage = (1-(norm_distance/max_distance))

    brightness = 255*percentage

    if brightness > 100:
        msg = mido.Message('note_on', note=60)
        output.send(msg)
        logger.info('On')


try:
    # Connect to midi
    devices = mido.get_output_names() # Get names of devices
    logger.info(devices)
    #try:
    #    output = mido.open_output('ESI MIDIMATE eX:ESI MIDIMATE eX MIDI 1 24:0')
    #except OSError as e:
    #    logger.error("Cannot find midi device")

    # Setup the GPIO for each sensor 
    for gpioPin in sensors:
        setupSensor(gpioPin)

    while True:
        for gpioPin in sensors:
            try:
                with timeout(1):
                    distance = measureSensor(gpioPin)
                    reading = str(gpioPin) + ": " + str(round(distance, 2))
                    logger.info(reading)
                    #changeLights(distance, output)
                    #time.sleep(0.1)
            except RuntimeError as e:
                logger.error(str(e))
                time.sleep(1)

        time.sleep(1)

except KeyboardInterrupt:
    logger.info("Stop")
    GPIO.cleanup()
