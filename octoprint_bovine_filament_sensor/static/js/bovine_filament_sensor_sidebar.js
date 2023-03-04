$(function(){
    function Bovine_filament_sensorSidebarViewModel(parameters){
        var self = this;

        self.settingsViewModel = parameters[0];
        //self.bovine_filament_sensorSettings = self.settingsViewModel.settings.plugins.bovine_filament_sensor;

        self.isSensorEnabled = ko.observable(undefined);
        self.remainingDistance = ko.observable(undefined);
        self.lastMotionDetected = ko.observable(undefined);
        self.isFilamentMoving = ko.observable(undefined);
        self.isConnectionTestRunning = ko.observable(false);

        //Returns the value in Yes/No if the Sensor is enabled 
        self.getSensorEnabledString = function(){
            var sensorEnabled = self.settingsViewModel.settings.plugins.bovine_filament_sensor.sensor_enabled();

            if(sensorEnabled){
                return "Yes";
            }
            else{
                return "No";
            }
        };

        // Returns the value of detection_method as string
        self.getDetectionMethodString = function(){
            var detectionMethod = self.settingsViewModel.settings.plugins.bovine_filament_sensor.detection_method();

            if(detectionMethod == 0){
                return "Timeout Detection";
            }
            else if(detectionMethod == 1){
                return "Distance Detection";
            }
        };

        self.getDetectionMethodBoolean = ko.pureComputed(function(){
            var detectionMethod = self.settingsViewModel.settings.plugins.bovine_filament_sensor.detection_method();

            if(detectionMethod == 0){
                return false;
            }
            else if(detectionMethod == 1){
                return true;
            }
        });

        self.onDataUpdaterPluginMessage = function(plugin, data){
            if(plugin !== "bovine_filament_sensor"){
                return;
            }
            
            var message = JSON.parse(data);
            self.remainingDistance( Math.round(message["_remaining_distance"]) );
            self.lastMotionDetected((new Date((message["_last_motion_detected"] * 1000))).toString());

            if(message["_filament_moving"] == true){
                self.isFilamentMoving("Yes");
            }
            else{
                self.isFilamentMoving("No");
            }

            if(message["_connection_test_running"] == true){
                self.isConnectionTestRunning("Running");
            }
            else{
                self.isConnectionTestRunning("Stopped");
            }
        };

        self.startConnectionTest = function(){
            $.ajax({
                url: API_BASEURL + "plugin/bovine_filament_sensor",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({ "command": "startConnectionTest" }),
                contentType: "application/json",
                success: self.RestSuccess
            });
        };

        self.stopConnectionTest = function(){
            $.ajax({
                url: API_BASEURL + "plugin/bovine_filament_sensor",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({ "command": "stopConnectionTest" }),
                contentType: "application/json",
                success: self.RestSuccess
            });
        };

        self.RestSuccess = function(response){
            return;
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: Bovine_filament_sensorSidebarViewModel,
        name: "Bovine_filament_sensorSidebarViewModel",
        dependencies: ["settingsViewModel"],
        elements: ["#sidebar_plugin_bovine_filament_sensor"]
    });
});
