import RPi.GPIO as GPIO
import threading
import time

class TimeoutDetector(threading.Thread):
    def __init__(self, thread_id, thread_name, pin,
                 max_idle_time, logger, data, callback=None):
        """Initialize Filament TimeoutDetector"""
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = thread_name
        self.callback = callback
        self._logger = logger
        self._data = data
        self.used_pin = pin
        self.max_idle_time = max_idle_time
        self._data.last_motion_detected = time.time()
        self.keep_running = True

        # Remove event, if already an event was set
        try:
            GPIO.remove_event_detect(pin)
        except ValueError:
            self._logger.warn("Pin %s not used before" % pin)
            
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.motion)

    def run(self):
        """Override run method of threading"""
        while self.keep_running:
            timespan = (time.time() - self._data.last_motion_detected)

            if timespan > self.max_idle_time:
                if self.callback is not None:
                    self.callback()

            time.sleep(0.250)

        GPIO.remove_event_detect(self.used_pin)

    # noinspection PyUnusedLocal
    def motion(self, pin):
        """Eventhandler for GPIO filament sensor signal.
        The new state of the GPIO pin is read and determinated.
        It is checked if motion is detected and printed to the console.
        """
        last_motion = time.time()
        self._data.last_motion_detected = last_motion
        self.callback(True)
        self._logger.debug("Motion detected at %s" % last_motion)
