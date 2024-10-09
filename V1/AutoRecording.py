import time
import utils

class AutoRecordingController:
    def __init__(self, CameraStateDB, GpsDB):
        print("AutoRecordingController Initialized")
        self.cam_state = CameraStateDB
        self.gps_points = GpsDB
        
        self.threshold_speed = 2.5              # Threshold velocity of the surfer (based on gps, m/s) to signal start/stop
        self.threshold_stop_hyster = 1.25        # These are used for introducing hysteresis to the start/stop condition
        self.threshold_start_hyster = 1.5
        self.timestamp_stop_hyster = 0          # These are used for the hysteresis timers
        self.timestamp_start_hyster = 0
        
        self.prev_lat, self.prev_lon = 0, 0
        self.prev_speed = 0
        self.gpsSpeed = 0
        self.prev_time = 0
        
        self.gpsSpeedAlpha = 0.8              # Exponential moving average for the gps speed calculation 
        self.cam_state.enable_auto_recording = True
        
    def check(self):
        self.updateGPSSpeed()
        
        if abs(self.gpsSpeed) < self.threshold_speed: # If under the threshold 
            self.timeflag_start_hyster = time.time()   
        else:                           
            self.timeflag_stop_hyster = time.time()
        
        if self.cam_state.enable_auto_recording and not self.cam_state.is_recording and time.time() - self.timeflag_start_hyster > self.threshold_start_hyster:
            print("AutoRecording Start Triggered")
            self.cam_state.start_recording = True
            
        if self.cam_state.enable_auto_recording and self.cam_state.is_recording and time.time() - self.timeflag_stop_hyster > self.threshold_stop_hyster:
            print("AutoRecording Stop Triggered")
            self.cam_state.start_recording = False
            
        #if not self.cam_state.enable_auto_recording and self.cam_state.is_recording:
            #print("AutoRecording Stop Triggered")
            #self.cam_state.start_recording = False
                  
    def updateGPSSpeed(self):
        current_time = self.gps_points.last_gps_time
        try:
            if self.prev_lat != 0 and self.prev_lon != 0:
                prev_loc = utils.Location(self.prev_lat, self.prev_lon)
                loc = utils.Location(self.gps_points.latest_gps_data['latitude'], self.gps_points.latest_gps_data['longitude'])
                distance = utils.get_distance_between_locations(loc, prev_loc) # Returns distance in meters
                time_diff = (current_time - self.prev_time)
                if time_diff > 0:
                    self.gpsSpeed =  distance / time_diff
                    self.gpsSpeed =  self.gpsSpeedAlpha * self.prev_speed + (1 - self.gpsSpeedAlpha) * self.gpsSpeed 
                    
            # Update previous values
            self.prev_lat = self.gps_points.latest_gps_data['latitude']
            self.prev_lon = self.gps_points.latest_gps_data['longitude']
            self.prev_time = current_time
            self.prev_speed = self.gpsSpeed
        except:
            print(Exception)

                    
