#!/usr/bin/python3

# ----------------------------- #
#          Instructions         #
# ----------------------------- #
#
#  - Run this script on the OctoPi
#  - > python3 connection_check.py
#  - To save some filament you can unload the
#    filament before and move it manually in the sensor


import RPi.GPIO as GPIO
import time

# GPIO pin configuration
PIN = 24
GPIO.setmode(GPIO.BCM)    # GPIO.BCM/GPIO.BOARD
GPIO.setup(PIN, GPIO.IN)

# Time in seconds
max_idle_time = 2

lastValue = GPIO.input(PIN)
# Get current time in seconds
lastMotion = time.time()


def main():
    try:
        GPIO.add_event_detect(PIN, GPIO.BOTH, callback=motion)

        while True:
            timespan = (time.time() - lastMotion)

            if timespan > max_idle_time:
                print("IDLE")
            else:
                print("MOVING")

            time.sleep(0.250)

    except KeyboardInterrupt:
        GPIO.remove_event_detect(PIN)
        print("Done")

# noinspection PyUnusedLocal
def motion(pin):
    global lastMotion
    lastMotion = time.time()
    print("Motion detected at " + str(lastMotion))


main()
