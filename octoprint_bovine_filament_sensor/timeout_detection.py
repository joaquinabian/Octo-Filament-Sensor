import RPi.GPIO as GPIO
import threading
import time

class TimeoutDetector(threading.Thread):
    def __init__(self, tID, tName, pUsedPin, pMaxNotMovingTime, pLogger, pData, pCallback=None):
        """Initialize Filament TimeoutDetector"""
        threading.Thread.__init__(self)
        self.threadID = tID
        self.name = tName
        self.callback = pCallback
        self._logger = pLogger
        self._data = pData
        self.used_pin = pUsedPin
        self.max_not_moving_time = pMaxNotMovingTime
        self._data.last_motion_detected = time.time()
        self.keepRunning = True

        # Remove event, if already an event was set
        try:
            GPIO.remove_event_detect(self.used_pin)
        except ValueError:
            self._logger.warn("Pin %s not used before" % pUsedPin)
            
        GPIO.add_event_detect(self.used_pin, GPIO.BOTH, callback=self.motion)

    # Override run method of threading
    def run(self):
        while self.keepRunning:
            timespan = (time.time() - self._data.last_motion_detected)

            if timespan > self.max_not_moving_time:
                if self.callback is not None:
                    self.callback()

            time.sleep(0.250)

        GPIO.remove_event_detect(self.used_pin)

    # Eventhandler for GPIO filament sensor signal
    # The new state of the GPIO pin is read and determinated.
    # It is checked if motion is detected and printed to the console.
    def motion(self, pPin):
        self._data.last_motion_detected = time.time()
        self.callback(True)
        self._logger.debug("Motion detected at " + str(self._data.last_motion_detected))
