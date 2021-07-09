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
          "midiChannel": 61,
          "active": True,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 70,
          "threshold": 35},
    "2": {"gpioPin": 17,
          "midiChannel": 62,
          "active": True,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 70,
          "threshold": 35},
    "3": {"gpioPin": 18,
          "midiChannel": 63,
          "active": False,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 70,
          "threshold": 35},
    "4": {"gpioPin": 27,
          "midiChannel": 64,
          "active": False,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 70,
          "threshold": 35},
    "5": {"gpioPin": 22,
          "midiChannel": 65,
          "active": False,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 70,
          "threshold": 35},
    "6": {"gpioPin": 23,
          "midiChannel": 66,
          "active": False,
          "lastVals": [],
          "nominal": 70,
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "threshold": 35},
    "7": {"gpioPin": 25,
          "midiChannel": 67,
          "active": False,
          "lastVals": [],
          "prevTrigger": False,
          "timeoutTasks": [],
          "noteLock": False,
          "nominal": 0,
          "threshold": 0},
}


def setupSensor(sensor):
    """Sets up a sensor by configuring the GPIO parameters for it, and 
    measures the nominal values to calculate a threshold trigger value."""
    try:
        if sensors[sensor]["active"] == True:
            # Timeout after 5s if the sensor isn't connected
            with timeout(3):
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
                print(f"[{sensor}] to nominal {nominal} cm")
    except:
        # sensors[sensor]["active"] = False # DANGER
        print(f"[{sensor}] is inactive, not modifying anything")


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
        #print(f"[{s}] four low vals continuously")
        return True
    else:
        return False


def detectMidiDevice():
    """Automatically detects primary midi device, ignoring the built in 
    virtual ones. Returns either none or the name of the device."""
    # Get devices
    devices = mido.get_output_names()  # Get names of devices
    
    # Remove built in devices for PI
    devices.remove('Midi Through:Midi Through Port-0 14:0')
    devices.remove('Midi Through:Midi Through Port-0 14:0')

    if len(devices) >= 1:
        output = mido.open_output(devices[0])
        print(f'[MIDI] Connected to MIDI on {devices[0]}')
        return output
    else:
        print('[MIDI] No midi devices found')
        return None


async def setTriggerTimeout(timeout, coro):
    """Creates a timeout for the trigger, so that we can send the off signal
    following the interval specified in the timeout parameter"""
    await asyncio.sleep(timeout)
    return await coro


async def sendMidiOff(s, output):
    # Reset note lock
    sensors[s]['noteLock'] = False

    # Send MIDI note
    note = sensors[s]["midiChannel"]
    msg = mido.Message('note_off', note=note)
    output.send(msg)
    print(f"[MIDI] Note OFF channel {note} from sensor {s}")


async def hello():
    # Setup websocket to ws-server.py
    uri = "ws://localhost:6789"
    async with websockets.connect(uri, ping_interval=None) as websocket:
        output = detectMidiDevice()

        # Read sensor data in a loop
        while True:
            # Count number of simultaneous sensors on
            simultaneous = 0

            for s in sensors:
                if sensors[s]["active"]:  # Only read active sensors
                    
                    with timeout(1): # Timeout if it takes too long
                        # TODO split into function this entire section 
                        pin = sensors[s]["gpioPin"]
                        #try:
                        # Measure distance
                        distance = measureSensor(pin)

                        # Calculate trigger
                        current_trigger = calculateTrigger(s, distance)

                        # Get previous trigger value
                        prev_trigger = sensors[s]['prevTrigger']

                        # Get the awaited timeout tasks
                        timeout_tasks = sensors[s]['timeoutTasks'] 
                        

                        if (sensors[s]['noteLock'] == False) and (current_trigger == True):
                            if output:
                                # Send MIDI note
                                note = sensors[s]["midiChannel"]
                                msg = mido.Message('note_on', note=note)
                                output.send(msg)
                                print(f"[MIDI] Note ON channel {note} from sensor {s}")
                            sensors[s]['noteLock'] = True

                        if current_trigger == True:
                            #print(len(timeout_tasks))
                            if len(timeout_tasks) == 0:
                            #if sensors[s]["timeoutTasks"]: 
                                # set first timeout task
                                sensors[s]["timeoutTasks"].append(asyncio.create_task(setTriggerTimeout(3, sendMidiOff(s, output))))
                                #sensors[s]["timeoutTasks"] = asyncio.create_task(setTriggerTimeout(3, sendMidiOff()))
                            else:
                                for my_task in sensors[s]["timeoutTasks"]:
                                    if not my_task.cancelled():
                                        #print('cancelling')
                                        my_task.cancel()
                                    else:
                                        #print('not cancelling')
                                        my_task = None
                                #print('setting')
                                #print('reserting')
                                sensors[s]["timeoutTasks"].append(asyncio.create_task(setTriggerTimeout(3, sendMidiOff(s, output))))
                            # pop last push first out
                        # Take action only if the previous states were off
                        ## check if there are active coroutines
                        # if (current_trigger == true) && (prev_trigger == false)
                            # send on signal and set off timer X secons

                        #if (current_trigger == true
                        #send_trigger = 
                        # Send over midi if triggered and we have midi
                        #if current_trigger and output:
                            # Determine note to send
                        #    note = sensors[s]["midiChannel"]

                            # Send MIDI note
                        #    msg = mido.Message('note_on', note=note)
                        #    output.send(msg)
                        #    print(f"[MIDI] Note on channel {note} from sensor {s}")
                        #33    #asyncio.create_task(setTriggerTimeout(3, sendMidiOff()))

                            # Add to simultaneous output
                        #simultaneous += 1

                        # TODO fix websockets and simultaneous
                        # Send over websockets
                        await websocket.send(json.dumps({
                            'value': distance,
                            'sensor': s,
                            'trigger': current_trigger,
                            'threshold': sensors[s]["threshold"]
                        }))
                        #except:
                        #    print(f"[{s}] Failed reading")
                        
                        # Safety sleep between each sensor
                        time.sleep(0.1)

            # Send special note if multiple sensors triggered at once
            if (simultaneous >= 2) and output:
                # Start counting channels at 70 for each simulataneous sense
                note = 70+simultaneous

                # Send MIDI note
                msg = mido.Message('note_on', note=note)
                output.send(msg)
                print(f"[MIDI] Simultaneous {simultaneous} sensors detected, sending note {note}")

            # Safety sleep between each loop
            await asyncio.sleep(0.01)
            # time.sleep(1)


if __name__ == "__main__":
    # Setup the GPIO for each sensor
    for sensor in sensors:
        setupSensor(sensor)

    # Start async event loop
    asyncio.get_event_loop().run_until_complete(hello())
