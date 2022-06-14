#! /usr/bin/env python3
from rpi_hardware_pwm import HardwarePWM
import time
import signal
import logging
import sys
import importlib

DEBUG = False           # Set to True for debug logging, should normally be False.
PWM_FREQ = 23000        # [Hz] The PWM frequency (number of pulses per second).
PWM_CHANNEL = 0         # The PWM channel to use.
WAIT_TIME = 2           # [s] The time to wait between each regulation cycle.

OFF_TEMP = 38           # [°C] The temperature below which to stop the fan.
MIN_TEMP = 42           # [°C] The temperature above which to start the fan.
MAX_TEMP = 60           # [°C] The temperature at which to operate at max fan speed.
FAN_OFF = 0             # [%] The fan duty to use when the fan is off.
FAN_START = 35          # [%] Fan startup duty (some fans require a higher startup than minimum duty).
FAN_LOW = 30            # [%] The lowest fan duty to use (check fan specs).
FAN_HIGH = 100          # [%] The highest fan duty to use.
FAN_GAIN = float(FAN_HIGH - FAN_LOW) / float(MAX_TEMP - MIN_TEMP)

curDuty = 0


def getCpuTemperature():
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        return float(f.read()) / 1000


def handleFanSpeed(pwm, temperature):

    global curDuty, pijuice
    if temperature > MIN_TEMP:
        delta = min(temperature, MAX_TEMP) - MIN_TEMP
        newDuty = FAN_LOW + delta * FAN_GAIN

    elif temperature < OFF_TEMP:
        newDuty = FAN_OFF

    elif curDuty > FAN_LOW:
        newDuty = FAN_LOW

    else:
        return

    if newDuty != curDuty and (newDuty == FAN_OFF or newDuty == FAN_LOW or newDuty == FAN_HIGH or abs(newDuty - curDuty) > 2):
        if curDuty == FAN_OFF:
            if DEBUG:
                logger.info("Temperature is %.1f°C, starting fan with duty %.f%%" % (temperature, newDuty))

            if pijuice:
                red, green, blue = calcLEDColor(newDuty)
                pijuice.status.SetLedBlink("D2", 5, [0, green, blue], 200, [0, 0, 0], 200)
            if FAN_START > newDuty:
                pwm.change_duty_cycle(FAN_START)
                time.sleep(2)

            pwm.change_duty_cycle(newDuty)
            if pijuice:
                pijuice.status.SetLedState("D2", [red, green, blue])

        elif newDuty == FAN_OFF:
            if DEBUG:
                logger.info("Temperature is %.1f°C, stopping fan" % temperature)

            pwm.change_duty_cycle(FAN_OFF)
            if pijuice:
                pijuice.status.SetLedState("D2", [0, 0, 0])

            time.sleep(2)

        else:
            if DEBUG:
                logger.info("Temperature is %.1f°C, setting duty to %.f%%" % (temperature, newDuty))

            pwm.change_duty_cycle(newDuty)
            if pijuice:
                pijuice.status.SetLedState("D2", calcLEDColor(newDuty))

        curDuty = newDuty


def calcLEDColor(duty):
    return [
        int(max(0, 50 - duty) * 2.56),
        int((50 - abs(duty - 50)) * 2.56),
        int(max(0, duty - 50) * 3.825)]


def initPiJuice():
    try:
        pijuice = importlib.import_module("pijuice")
        return pijuice.PiJuice(1, 0x14)
    except ImportError:
        return None


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
logger.info("Starting automatic PWM fan regulator for PWM channel %d with PWM frequency %dHz and settings:" % (PWM_CHANNEL, PWM_FREQ))
logger.info("  Duties: OFF=%d%%, START=%d%%, LOW=%d%%, HIGH=%d%%" % (FAN_OFF, FAN_START, FAN_LOW, FAN_HIGH))
logger.info("  Temperatures: OFF=%.1f°C, MIN=%.1f°C, MAX=%.1f°C" % (OFF_TEMP, MIN_TEMP, MAX_TEMP))

pwm = HardwarePWM(pwm_channel=PWM_CHANNEL, hz=PWM_FREQ)

pijuice = initPiJuice()

try:
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    pwm.start(FAN_OFF)
    time.sleep(WAIT_TIME)
    while True:
        handleFanSpeed(pwm, getCpuTemperature())
        time.sleep(WAIT_TIME)

except KeyboardInterrupt:
    pass

finally:
    pwm.stop()
    if pijuice:
        pijuice.status.SetLedState("D2", [0, 0, 0])
    logger.info("Automatic PWM fan regulator for PWM channel %d was stopped" % PWM_CHANNEL)
