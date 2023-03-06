import json

class DetectionData(object):
    @property
    def remaining_distance(self):
        return self._remaining_distance

    @remaining_distance.setter
    def remaining_distance(self, value):
        self._remaining_distance = value
        self.update_gui()

    @property
    def print_started(self):
        return self._print_started

    @print_started.setter
    def print_started(self, value):
        self._print_started = value

    @property
    def last_e(self):
        return self._last_e

    @last_e.setter
    def last_e(self, value):
        self._last_e = value

    @property
    def current_e(self):
        return self._current_e

    @current_e.setter
    def current_e(self, value):
        self._current_e = value

    @property
    def absolut_extrusion(self):
        return self._absolut_extrusion

    @absolut_extrusion.setter
    def absolut_extrusion(self, value):
        self._absolut_extrusion = value

    @property
    def last_motion_detected(self):
        return self._last_motion_detected

    @last_motion_detected.setter
    def last_motion_detected(self, value):
        self._last_motion_detected = value
        self.update_gui()

    @property
    def filament_moving(self):
        return self._filament_moving

    @filament_moving.setter
    def filament_moving(self, value):
        self._filament_moving = value
        self.update_gui()

    @property
    def connection_test_running(self):
        return self._connection_test_running

    @connection_test_running.setter
    def connection_test_running(self, value):
        self._connection_test_running = value
        self.update_gui()

    def __init__(self, remaining_distance, absolut_extrusion, callback=None):
        self._remaining_distance = remaining_distance
        self._absolut_extrusion = absolut_extrusion
        self.START_DISTANCE_OFFSET = 7
        self.update_gui = callback

        # Default values
        self._print_started = False
        self._last_e = -1
        self._current_e = -1
        self._last_motion_detected = ""
        self._connection_test_running = None
        self._filament_moving = False

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
