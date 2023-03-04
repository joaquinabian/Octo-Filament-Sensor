# coding=utf-8

import RPi.GPIO as GPIO
from datetime import datetime
from time import sleep
from octoprint.plugin import StartupPlugin, AssetPlugin, EventHandlerPlugin
from octoprint.plugin import TemplatePlugin, SettingsPlugin, SimpleApiPlugin
from octoprint.events import Events
from octoprint_bovine_filament_sensor.timeout_detection import TimeoutDetector
from octoprint_bovine_filament_sensor.data import DetectionData


class Bovine_filament_sensorPlugin(StartupPlugin, EventHandlerPlugin, TemplatePlugin,
                                   SettingsPlugin, AssetPlugin, SimpleApiPlugin):

    def __init__(self):
        self.print_started = False
        self.last_movement_time = None
        self.lastE = -1
        self.currentE = -1
        self.START_DISTANCE_OFFSET = 7
        self.send_code = False
        self.sensor_thread = None
        self._data = None

    def initialize(self):
        self._logger.info("Q-initialize")
        self._data = DetectionData(self.sensor_detection_distance, True,
                                   self.update_ui)

    def on_after_startup(self):
        self._logger.info("Bovine Filament Sensor started")

        self._logger.info("Running RPi.GPIO version '%s'" % GPIO.VERSION)
        if GPIO.VERSION < "0.6":    # Need >= 0.6 for edge detection
            raise Exception("RPi.GPIO must be greater than 0.6")
        GPIO.setwarnings(False)     # Disable GPIO warnings

        self._setup_sensor()

    @property
    def sensor_pin(self):
        return int(self._settings.get(["sensor_pin"]))

    @property
    def sensor_pause_print(self):
        return self._settings.get_boolean(["sensor_pause_print"])

    @property
    def detection_method(self):
        return int(self._settings.get(["detection_method"]))

    @property
    def sensor_enabled(self):
        return self._settings.get_boolean(["sensor_enabled"])

    @property
    def pause_command(self):
        return self._settings.get(["pause_command"])
    
    @property
    def mode(self):
        return int(self._settings.get(["mode"]))
    
    # Distance detection
    @property
    def sensor_detection_distance(self):
        return int(self._settings.get(["sensor_detection_distance"]))

    # Timeout detection
    @property
    def sensor_max_not_moving(self):
        return int(self._settings.get(["sensor_max_not_moving"]))

    # Initialization methods
    def _setup_sensor(self):
        
        # Clean up before intializing again (ports could already be in use)
        if self.mode == 0:
            self._logger.info("Using Board Mode")
            GPIO.setmode(GPIO.BOARD)
        else:
            self._logger.info("Using BCM Mode")
            GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.sensor_pin, GPIO.IN)

        # Add reset_distance if detection_method is distance_detection
        if self.detection_method == 1:
            # Remove event first, because it might have been in use already
            try:
                GPIO.remove_event_detect(self.sensor_pin)
            except ValueError:
                self._logger.warn(
                    "Pin " + str(self.sensor_pin) + " not used before")

            GPIO.add_event_detect(self.sensor_pin, GPIO.BOTH,
                                  callback=self.reset_distance)

        if not self.sensor_enabled:
            self._logger.info("Motion sensor is deactivated")

        self._data.filament_moving = False
        self.sensor_thread = None

        self.load_bovine_filament_sensor_data()
    
    def load_bovine_filament_sensor_data(self):
        self._logger.info("loading bovine filament sensor data")
        self._data.remaining_distance = self.sensor_detection_distance    

    def get_settings_defaults(self):
        """SettingsPlugin mixin.
        Put your plugin's default settings here.
        """
        self._logger.info("Q-get_settings_defaults")
        return dict(
            # Motion sensor
            mode=0,               # Board Mode
            sensor_enabled=True,  # Sensor detection is enabled by default
            sensor_pin=24,        #
            detection_method=0,   # 0/1 = timeout/distance detection

            # Distance detection
            # Recommended detection distance from Marlin would be 7
            sensor_detection_distance=15,

            # Timeout detection
            # Maximum time no movement is detected - default continously
            sensor_max_not_moving=45,

            pause_command="M600",
        )

    def on_settings_save(self, data):
        SettingsPlugin.on_settings_save(self, data)
        self._setup_sensor()

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True)]

    def get_assets(self):
        """AssetPlugin mixin.
        Define your plugin's asset files to automatically include 
        in the core UI here."""
        return dict(js=["js/bovine_filament_sensor_sidebar.js",
                        "js/bovine_filament_sensor_settings.js"])

    ####  Sensor methods  ###

    def stop_connection_test(self):
        """Connection tests"""
        if self.sensor_thread is not None and self.sensor_thread.name == "ConnectionTest":
            self.sensor_thread.keepRunning = False
            self.sensor_thread = None
            self._data.connection_test_running = False
            self._logger.info("Connection test stopped")
        else:
            self._logger.info("Connection test is not running")

    def start_connection_test(self):
        """Connection tests"""
        CONNECTION_TEST_TIME = 2
        if self.sensor_thread is None:
            self.sensor_thread = TimeoutDetector(1, "ConnectionTest",
                                                 self.sensor_pin,
                                                 CONNECTION_TEST_TIME,
                                                 self._logger, self._data,
                                                 pCallback=self.connection_test_callback)
            self.sensor_thread.start()
            self._data.connection_test_running = True
            self._logger.info("Connection test started")

    def sensor_start(self):
        """Starts the motion sensor if the sensors are enabled."""
        
        self._logger.debug("Sensor enabled: %s" % self.sensor_enabled)

        if self.sensor_enabled:
            if self.mode == 0:
                self._logger.debug("GPIO mode: Board Mode")
            else:
                self._logger.debug("GPIO mode: BCM Mode")
            self._logger.debug("GPIO pin: " + str(self.sensor_pin))

            # Distance detection
            if self.detection_method == 1:
                self._logger.info("Motion sensor started: Distance detection")
                self._logger.debug("Detection Mode: Distance detection")
                self._logger.debug(
                    "Distance: %s" % self.sensor_detection_distance)

            # Timeout detection
            elif self.detection_method == 0 and self.sensor_thread is None:
                self._logger.debug("Detection Mode: Timeout detection")
                self._logger.debug(
                    "Timeout: %s" % self.sensor_max_not_moving)

                # Start Timeout_Detection thread
                self.sensor_thread = TimeoutDetector(
                    1, "SensorTimeoutDetectionThread",
                    self.sensor_pin,
                    self.sensor_max_not_moving,
                    self._logger, self._data,
                    pCallback=self.printer_change_filament
                )
                self.sensor_thread.start()
                self._logger.info("Motion sensor started: Timeout detection"
                                          )
            self.send_code = False
            self._data.filament_moving = True

    # Stop the motion_sensor thread
    def sensor_stop_thread(self):
        if self.sensor_thread is not None:
            self.sensor_thread.keepRunning = False
            self.sensor_thread = None
            self._logger.info("Motion sensor stopped")

    def ring_bell(self):
        GPIO.setup(21, GPIO.OUT)
        for n in range(25):
            GPIO.output(21, True)  # Turn OFF LED
            sleep(2)
            GPIO.output(21, False)  # Turn ON LED
            sleep(1)

    # Sensor callbacks
    def printer_change_filament(self, dummy):
        """Send configured pause command to the printer to interrupt the print"""
        _ = dummy
        # Check if stop signal was already sent
        if not self.send_code:
            self._logger.error("Motion sensor detected no movement")
            self._logger.info("Pause command: " + self.pause_command)
            if self.pause_command == "@Mu":
                self._logger.info("Muuuuuuuuu!!!!")
                self.ring_bell()
            else:
                self._printer.commands(self.pause_command)
                self.send_code = True
            self._data.filament_moving = False
            self.lastE = -1  # Set to -1, so it ignores the first test then continues

    # Reset the distance, if the remaining distance is smaller than the new value
    def reset_distance(self, pPin):
        _ = pPin
        self._logger.debug("Motion sensor detected movement")
        self.send_code = False
        self.last_movement_time = datetime.now()
        if self._data.remaining_distance < self.sensor_detection_distance:
            self._data.remaining_distance = self.sensor_detection_distance
            self._data.filament_moving = True

    def init_distance_detection(self):
        """Initialize the distance detection values"""
        self.lastE = -1.0
        self.currentE = 0.0
        self.reset_remaining_distance()

    def reset_remaining_distance(self):
        """ Reset the remaining distance on start or resume.
        START_DISTANCE_OFFSET is used for the (re-)start sequence.

        """
        self._data.remaining_distance = self.sensor_detection_distance + \
                                        self.START_DISTANCE_OFFSET

    def calc_distance(self, pE):
        """Calculate the remaining distance"""
        if self.detection_method == 1:

            # First check if need continue after last move
            if self._data.remaining_distance > 0:

                # Calculate deltaDistance if absolute extrusion
                if self._data.absolut_extrusion:
                    # LastE is not used and set to the same value as currentE.
                    # Occurs on first run or after resuming
                    if self.lastE < 0:
                        self._logger.info(
                            "Ignoring run with a negative value. "
                            "Setting LastE to PE: %s = %s" % (self.lastE, pE))
                        self.lastE = pE
                    else:
                        self.lastE = self.currentE

                    self.currentE = pE

                    deltaDistance = self.currentE - self.lastE
                    rounded_delta = round(deltaDistance, 3)
                    self._logger.debug(
                        "CurrentE: %s - LastE: %s = %s" % (self.currentE, self.lastE, rounded_delta))

                # deltaDistance is just position if relative extrusion
                else:
                    deltaDistance = float(pE)
                    rounded_delta = round(deltaDistance, 3)
                    self._logger.debug(
                        "Relative Extrusion = %s" % rounded_delta)

                if deltaDistance > self.sensor_detection_distance:
                    # Calculate the deltaDistance modulo the sensor_detection_distance
                    # Sometimes the polling of M114 is inaccurate so that with the next poll
                    # very high distances are put back followed by zero distance changes.
                    deltaDistance = deltaDistance % self.sensor_detection_distance

                current_remaining = self._data.remaining_distance - deltaDistance

                self._logger.debug(
                    f"Remaining: {self._data.remaining_distance} - Extruded: {deltaDistance} = {current_remaining}"
                )
                self._data.remaining_distance = current_remaining

            else:
                # Only pause the print if it's been over 5 seconds since the last movement.
                # Stops pausing when the CPU gets hung up.
                timedelta = datetime.now() - self.last_movement_time
                if timedelta.total_seconds() > 10:
                    self.printer_change_filament(None)
                else:
                    self._logger.debug(
                        "Ignored pause command due to 5 second rule")

    def update_ui(self):
        self._plugin_manager.send_plugin_message(self._identifier,
                                                 self._data.to_json())

    def connection_test_callback(self, pMoving=False):
        self._data.filament_moving = pMoving

    # Remove motion sensor thread if the print is paused
    def print_paused(self, pEvent=""):
        self.print_started = False
        self._logger.info("%s: Pausing filament sensors." % pEvent)
        if self.sensor_enabled and self.detection_method == 0:
            self.sensor_stop_thread()

    # Events
    def on_event(self, event, payload):
        _ = payload
        if event is Events.PRINT_STARTED:
            self.stop_connection_test()
            self.print_started = True
            if self.detection_method == 1:
                self.init_distance_detection()

        elif event is Events.PRINT_RESUMED:
            self.print_started = True

            # If distance detection is used reset the remaining distance,
            # otherwise the print is not resuming anymore
            if self.detection_method == 1:
                self.reset_remainin_distance()

            self.sensor_start()

        # Start motion sensor on first G1 command
        elif event is Events.Z_CHANGE:
            if self.print_started:
                self.sensor_start()

                # Set print_started to 'False' 
                # to prevent that the starting command is called multiple times
                self.print_started = False

        # Disable sensor
        elif event in (Events.PRINT_DONE,
                       Events.PRINT_FAILED,
                       Events.PRINT_CANCELLED,
                       Events.ERROR
                       ):
            self._logger.info("%s: Disabling filament sensors." % event)
            self.print_started = False
            if self.sensor_enabled and self.detection_method == 0:
                self.sensor_stop_thread()

        # Disable motion sensor if paused
        elif event is Events.PRINT_PAUSED:
            self.print_paused(event)

        elif event is Events.USER_LOGGED_IN:
            self.update_ui()

    # API commands
    def get_api_commands(self):
        return dict(
            startConnectionTest=[],
            stopConnectionTest=[]
        )

    def on_api_command(self, command, data):
        _ = data
        self._logger.info("API: " + command)
        if command == "startConnectionTest":
            self.start_connection_test()
            return flask.make_response("Started connection test", 204)
        elif command == "stopConnectionTest":
            self.stop_connection_test()
            return flask.make_response("Stopped connection test", 204)
        else:
            return flask.make_response("Not found", 404)

    # noinspection PyUnusedLocal
    def distance_detection(self, comm_instance, phase, cmd, cmd_type, gcode,
                           *args, **kwargs):
        """Hook to interpret GCode commands sent to the printer.
        G92: Reset the distance detection values.
        G0 or G1: Calculate the remaining distance.
        """
        
        # Only performed if distance detection is used
        if self.detection_method == 1 and self.sensor_enabled:
            # G0/G1 for linear moves and G2/G3 for circle movements
            if gcode in ["G0", "G1", "G2", "G3"]:
                commands = cmd.split(" ")

                for command in commands:
                    if command.startswith("E"):
                        extruder = command[1:]
                        self._logger.debug("----- RUNNING calc_distance -----")
                        self._logger.debug(
                            "Found extrude command in '%s' with value: %s") % (cmd, extruder)
                        self.calc_distance(float(extruder))

            # G92 reset extruder
            elif gcode == "G92":
                if self.detection_method == 1:
                    self.init_distance_detection()
                self._logger.debug(
                    "Found G92 command in '" + cmd + "' : Reset Extruders")

            # M82 absolut extrusion mode
            elif gcode == "M82":
                self._data.absolut_extrusion = True
                self._logger.info(
                    "Found M82 command in '%s' : Absolut extrusion") % cmd
                self.lastE = 0

            # M83 relative extrusion mode
            elif gcode == "M83":
                self._data.absolut_extrusion = False
                self._logger.info(
                    "Found M83 command in '%s' : Relative extrusion") % cmd
                self.lastE = 0

        return cmd    


    def get_update_information(self):
        """Software Update Hook.
        Define the configuration for your plugin to use with the
        Software Update Plugin here.
        For details, see:
        https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        """
        
        return {
            "bovine_filament_sensor": {
                "displayName": "Bovine_filament_sensor Plugin",
                "displayVersion": self._plugin_version,

                # version check: GitHub repository
                "type": "github_release",
                "user": "joaquinabian",
                "repo": "OctoPrint-Bovine_filament_sensor",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/joaquinabian/OctoPrint-Bovine_filament_sensor/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name 
__plugin_name__ = "Bovine_filament_sensor"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Bovine_filament_sensorPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.distance_detection
    }


def __plugin_check__():
    try:
        import RPi.GPIO
    except ImportError:
        return False

    return True
