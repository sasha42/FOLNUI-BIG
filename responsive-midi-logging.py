# coding: utf-8
import time
import RPi.GPIO as GPIO
import mido
import logging
from rlog import RedisHandler
import sys
from timeout import timeout
import asyncio
import websockets
import json
import statistics

# Use redis for logs
# logger = logging.getLogger()
# logger.addHandler(RedisHandler(channel='logs'))
# logger.setLevel(logging.DEBUG)

# Log stdout stuff
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s: %(message)s', "%H:%M:%S")
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# Use global state for whether someone is detected under sensor
# detected = False

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define GPIO to use on Pi
# GPIO_TRIGECHO = 4
# GPIO_PINS = [4, 17, 18, 27, 22, 23, 25]
# sensors = [4, 17, 18, 27, 22, 25]
# sensors = [4, 17, 18]
# sensors = [4, 17]
sensors = {
    "1": {"gpioPin": 4,
          "active": True,
          "nominal": 0,
          "threshold": 0},
    "2": {"gpioPin": 17,
          "active": True,
          "nominal": 0,
          "threshold": 0},
    "3": {"gpioPin": 18,
          "active": True,
          "nominal": 0,
          "threshold": 0},
    "4": {"gpioPin": 27,
          "active": True,
          "nominal": 0,
          "threshold": 0},
    "5": {"gpioPin": 22,
          "active": True,
          "nominal": 0,
          "threshold": 0},
    "6": {"gpioPin": 23,
          "active": False,
          "nominal": 0,
          "threshold": 0},
    "7": {"gpioPin": 25,
          "active": True,
          "nominal": 0,
          "threshold": 0},
}

# logger.info("Ultrasonic Measurement")


def setupSensor(sensor):
    """Sets up a sensor by configuring the GPIO parameters for it"""
    try:
        with timeout(5):
            # Get the sensor pin
            pin = sensors[sensor]["gpioPin"]

            # Set pins as output and input
            GPIO.setup(pin, GPIO.OUT)  # Initial state as output

            # Set trigger to False (Low)
            GPIO.output(pin, False)

            # Measure nominal distance to set threshold
            distanceMeasurements = []
            for i in range(10):
                distanceMeasurements.append(measureSensor(pin))

            # Get the mode (most common value) of nominal distances
            nominal = statistics.mode(distanceMeasurements)

            # Set the nominal value and threshold on global variable
            #global sensors
            sensors[sensor]["nominal"] = nominal
            sensors[sensor]["threshold"] = int(nominal/2)  # use as sensitivity
            print(f"Set {sensor} to nominal {nominal} cm")
    except:
        sensors[sensor]["active"] = False
        print(f"Set {sensor} to inactive")


def measureSensor(gpioPin):
    """Measures the distnace of an individual sensor"""
    # Pulse the trigger/echo line to initiate a measurement
    GPIO.output(gpioPin, True)
    time.sleep(0.00001)
    GPIO.output(gpioPin, False)

    # ensure start time is set in case of very quick return
    start = time.time()

    # set line to input to check for start of echo response
    GPIO.setup(gpioPin, GPIO.IN)
    while GPIO.input(gpioPin) == 0:
        start = time.time()

    # Wait for end of echo response
    while GPIO.input(gpioPin) == 1:
        stop = time.time()

    GPIO.setup(gpioPin, GPIO.OUT)
    GPIO.output(gpioPin, False)

    time.sleep(0.00001)
    elapsed = stop-start
    distance = (elapsed * 34300)/2.0
    return int(distance)


def measure():
  # This function measures a distance
  # Pulse the trigger/echo line to initiate a measurement
    GPIO.output(GPIO_TRIGECHO, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGECHO, False)
  # ensure start time is set in case of very quick return
    start = time.time()

  # set line to input to check for start of echo response
    GPIO.setup(GPIO_TRIGECHO, GPIO.IN)
    while GPIO.input(GPIO_TRIGECHO) == 0:
        start = time.time()

  # Wait for end of echo response
    while GPIO.input(GPIO_TRIGECHO) == 1:
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


async def hello():
    uri = "ws://localhost:6789"
    # while True:
    # websocket= await websockets.connect(uri, ping_interval=None)

    # if not websocket.open:
    #    print ('Websocket NOT connected. Trying to reconnect.')
    #    websocket= await websockets.connect(uri, ping_interval=None)
    #    msg = json.dumps({"event":"pusher:subscribe","data":{"channel":"order_book"}})
    #    await websocket.send(msg)
    async with websockets.connect(uri, ping_interval=None) as websocket:
        # try:
        # Connect to midi
        devices = mido.get_output_names()  # Get names of devices
        # logger.info(devices)
        # try:
        #    output = mido.open_output('ESI MIDIMATE eX:ESI MIDIMATE eX MIDI 1 24:0')
        # except OSError as e:
        #    logger.error("Cannot find midi device")

        while True:
            for gpioPin in sensors:
                try:
                    with timeout(1):
                        try:
                            distance = measureSensor(gpioPin)
                        except:
                            print(f"fail on {gpioPin}")
                        clean_dist = int(distance)
                        reading = str(gpioPin) + ": " + str(clean_dist)
                        # logger.info(reading)
                        await websocket.send(json.dumps({'value': clean_dist, 'sensor': gpioPin}))
                        # changeLights(distance, output)
                        time.sleep(0.01)
                except RuntimeError as e:
                    logger.error(str(e))
                    time.sleep(1)

            # await websocket.ping()
            # await websocket.send(json.dumps({'action': 'plus'}))
            await asyncio.sleep(0.01)
            # time.sleep(1)

        # except KeyboardInterrupt:
        #    logger.info("Stop")
        #    GPIO.cleanup()

if __name__ == "__main__":
    # Setup the GPIO for each sensor
    for sensor in sensors:
        setupSensor(sensor)
    
    # Start async event loop
    asyncio.get_event_loop().run_until_complete(hello())
