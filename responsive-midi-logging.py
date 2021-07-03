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


# Use BCM GPIO references instead of physical pin numbers
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# Configure the sensors used: map their names and midi channels to
# GPIO pins, set up nominal and threshold values
sensors = {
    "1": {"gpioPin": 4,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "2": {"gpioPin": 17,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "3": {"gpioPin": 18,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "4": {"gpioPin": 27,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "5": {"gpioPin": 22,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "6": {"gpioPin": 23,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35},
    "7": {"gpioPin": 25,
          "active": False,
          "lastVals": [],
          "nominal": 0,
          "threshold": 0},
}


def setupSensor(sensor):
    """Sets up a sensor by configuring the GPIO parameters for it, and 
    measures the nominal values to calculate a threshold trigger value."""
    try:
        # Timeout after 5s if the sensor isn't connected
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
        # sensors[sensor]["active"] = False # DANGER
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


# def calculateTrigger(s, distance):
#    """Calculates whether to trigger a signal based on activity
#    below the sensor"""
#
#    # Append the latest value
#    sensors[s]["lastVals"].append(distance)
#
#    # Make sure we only have 3 vals
#    sensors[s]["lastVals"] = sensors[s]["lastVals"][-3:]
#
#    # Get mean of last 3 vals
#    value = 0
#    for v in sensors[s]["lastVals"]:
#        value += v
#
#    #print(f"[{s}] value {value}")
#    # If less than 25 for last 3 values
#    if value/3 < 30:
#        print(f"[{s}] value {int(value/3)} actually close {s}")


def calculateTrigger(s, distance):
    """Calculates whether to trigger a signal based on activity
    below the sensor"""

    # Append the latest value
    sensors[s]["lastVals"].append(distance)

    # Make sure we only have 3 vals
    sensors[s]["lastVals"] = sensors[s]["lastVals"][-2:]

    # Get mean of last 3 vals
    value = 0
    for v in sensors[s]["lastVals"]:
        if v < sensors[s]['threshold']:
            value += 1
        else:
            value -= 1

    #print(f"[{s}] value {value}")
    # If less than 25 for last 3 values
    if value >= 2:
        print(f"[{s}] four low vals continuously")
        return True
    else:
        return False


async def hello():
    # Setup websocket to ws-server.py
    uri = "ws://localhost:6789"
    async with websockets.connect(uri, ping_interval=None) as websocket:
        # Connect to midi
        # try:
        devices = mido.get_output_names()  # Get names of devices
        print(devices)
        # logger.info(devices)
        # try:
        #    output = mido.open_output('ESI MIDIMATE eX:ESI MIDIMATE eX MIDI 1 24:0')
        # except OSError as e:
        #    logger.error("Cannot find midi device")

        # Read sensor data in a loop
        while True:
            for s in sensors:
                if sensors[s]["active"]:  # Only read active sensors
                    with timeout(1): # Timeout if it takes too long
                        pin = sensors[s]["gpioPin"]
                        try:
                            # Measure distance
                            distance = measureSensor(pin)

                            # Calculate trigger
                            trigger = calculateTrigger(s, distance)

                            # Send over midi if triggered
                            if trigger:
                                print('we should send over midi')

                            # Send over websockets
                            await websocket.send(json.dumps({
                                'value': distance,
                                'sensor': s,
                                'trigger': trigger,
                                'threshold': sensors[s]["threshold"]
                            }))
                        except:
                            print(f"Failed reading {s}")
                        
                        # Safety sleep between each sensor
                        time.sleep(0.01)

            # Safety sleep between each loop
            await asyncio.sleep(0.01)
            # time.sleep(1)


if __name__ == "__main__":
    # Setup the GPIO for each sensor
    for sensor in sensors:
        setupSensor(sensor)

    # Start async event loop
    asyncio.get_event_loop().run_until_complete(hello())
