#!/usr/bin/python
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import time

TACH = 24       # The fan's tachometer output GPIO pin number.
PULSE = 2       # The number of pulses per revolution, most fans seems to use two.
WAIT_TIME = 1   # [s] The time to wait between each refresh.

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TACH, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Pull up to 3.3V

# Setup variables
t = time.time()
rpm = 0


# Caculate pulse frequency and RPM
def fell(n):
    global t
    global rpm

    dt = time.time() - t
    if dt < 0.002:
        return  # Reject spuriously short pulses

    freq = 1 / dt
    rpm = (freq / PULSE) * 60
    t = time.time()


# Add event to detect
GPIO.add_event_detect(TACH, GPIO.FALLING, fell)

try:
    while True:
        print("%.f RPM" % rpm)
        rpm = 0
        time.sleep(1)   # Detect every second

except KeyboardInterrupt:   # trap a CTRL+C keyboard interrupt
    GPIO.cleanup()          # resets all GPIO ports used by this function
