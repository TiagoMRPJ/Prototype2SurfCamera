import redis
import pickle
import json

def get_connection():
    return redis.Redis()


class RedisClient:

    def __init__(self, connection):
        """Initialize client."""
        self.r = connection

    def set(self, key, value, **kwargs):
        """Store a value in Redis."""
        return self.r.set(key, pickle.dumps(value), **kwargs)

    def set_initial(self, key, value):
        """Store a value in Redis."""
        if not self.get(key):
            self.set(key, value)

    def get(self, key):
        """Retrieve a value from Redis."""
        val = self.r.get(key)
        if val:
            return pickle.loads(val)
        return None

    def dump(self, keys, filename):
        data = {}
        for k in keys:
            data[k] = self.get(k)
        print("storing configuration: %s" % json.dumps(data, indent=2))
        with open(filename, "w") as fp:
            json.dump(data, fp, indent=2)

    def load(self, filename):
        data = {}
        with open(filename) as fp:
            data = json.load(fp)
        print("configuration loaded: %s" % json.dumps(data, indent=2))
        for k in data:
            self.set(k, data[k])
            

class GPSData:
    def  __init__(self, connection):
        self.client = RedisClient(connection)
        self.client.set_initial("camera_origin", { "latitude": 0, "longitude": 0 })          # Coordinates of the camera's location -> Calibrate to change this
        self.client.set_initial("camera_heading_coords", { "latitude": 0, "longitude": 0})   # Coordinates of camera's 0º heading -> Calibrate to change this
        self.client.set_initial("camera_heading_angle", 0)
        self.client.set_initial("latest_gps_data", { "latitude": 0, "longitude": 0})         # Latest coordinates received from the Tracker
        self.client.set_initial("reads_per_second", 0)                                       # Variable to store how many readings per second we're taking from the radio
        self.client.set_initial("gps_fix", False)                                            # Flag to indicate th
        self.client.set_initial("transmission_fix", False)  
        self.client.set_initial("new_reading", False)                 # Flag to indicate a new reading has come in
        self.client.set_initial("tilt_offset", 0 )                      # Used to manually fine adjust tilt calibration
        self.client.set_initial("camera_vertical_distance", 3.5)        # Variable to store the fixed value of the camera vertical position 
        
    @property
    def camera_origin(self):
        return self.client.get("camera_origin")

    @camera_origin.setter
    def camera_origin(self, value):
        self.client.set("camera_origin", value)
        
    @property
    def camera_heading_coords(self):
        return self.client.get("camera_heading_coords")

    @camera_heading_coords.setter
    def camera_heading_coords(self, value):
        self.client.set("camera_heading_coords", value)
        
    @property
    def camera_heading_angle(self):
        return self.client.get("camera_heading_angle")

    @camera_heading_angle.setter
    def camera_heading_angle(self, value):
        self.client.set("camera_heading_angle", value)
        
    @property
    def latest_gps_data(self):
        return self.client.get("latest_gps_data")

    @latest_gps_data.setter
    def latest_gps_data(self, value):
        self.client.set("latest_gps_data", value)
        
    @property
    def gps_fix(self):
        return self.client.get("gps_fix")

    @gps_fix.setter
    def gps_fix(self, value):
        self.client.set("gps_fix", value)
        
    @property
    def transmission_fix(self):
        return self.client.get("transmission_fix")

    @transmission_fix.setter
    def transmission_fix(self, value):
        self.client.set("transmission_fix", value)
        
    @property
    def new_reading(self):
        return self.client.get("new_reading")

    @new_reading.setter
    def new_reading(self, value):
        self.client.set("new_reading", value)
        
    @property
    def tilt_offset(self):
        return self.client.get("tilt_offset")

    @tilt_offset.setter
    def tilt_offset(self, value):
        self.client.set("tilt_offset", value)
        
    @property
    def camera_vertical_distance(self):
        return self.client.get("camera_vertical_distance")

    @camera_vertical_distance.setter
    def camera_vertical_distance(self, value):
        self.client.set("camera_vertical_distance", value)
        

class Commands:
    def  __init__(self, connection):
        self.client = RedisClient(connection)
        self.client.set_initial("camera_calibrate_origin", False)    # Flag utilized to start the origin calibration process
        self.client.set_initial("camera_calibrate_heading", False)   # Flag utilized to start the heading calibration process
        self.client.set_initial("camera_zoom_value", 5)             # Zoom value to apply between 1 and 30
        self.client.set_initial("camera_apply_zoom_value", False)
        self.client.set_initial("tracking_enabled", False)            # Flag utilized to toggle tracking        
        
    @property
    def camera_calibrate_origin(self):
        return self.client.get("camera_calibrate_origin")

    @camera_calibrate_origin.setter
    def camera_calibrate_origin(self, value):
        self.client.set("camera_calibrate_origin", value)
        
    @property
    def camera_calibrate_heading(self):
        return self.client.get("camera_calibrate_heading")

    @camera_calibrate_heading.setter
    def camera_calibrate_heading(self, value):
        self.client.set("camera_calibrate_heading", value)
        
    @property
    def camera_zoom_value(self):
        return self.client.get("camera_zoom_value")

    @camera_zoom_value.setter
    def camera_zoom_value(self, value):
        self.client.set("camera_zoom_value", value)
        
    @property
    def tracking_enabled(self):
        return self.client.get("tracking_enabled")

    @tracking_enabled.setter
    def tracking_enabled(self, value):
        self.client.set("tracking_enabled", value)
        
class CameraState:
    def __init__(self, connection):
        self.client = RedisClient(connection)
        self.client.set_initial("start_recording", False)
        self.client.set_initial("is_recording", False)
        self.client.set_initial("enable_auto_recording", False)

    @property
    def is_recording(self):
        return self.client.get("is_recording")

    @is_recording.setter
    def is_recording(self, v):
        self.client.set("is_recording", v)

    @property
    def image(self):
        return self.client.get("state_image")

    @image.setter
    def image(self, v):
        self.client.set("state_image", v)

    @property
    def start_recording(self):
        return self.client.get("start_recording")

    @start_recording.setter
    def start_recording(self, v):
        self.client.set("start_recording", v)
        
    @property
    def enable_auto_recording(self):
        return self.client.get("enable_auto_recording")

    @enable_auto_recording.setter
    def enable_auto_recording(self, v):
        self.client.set("enable_auto_recording", v)