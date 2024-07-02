import db
import math
import utils
import time
import numpy as np
import IOBoardDriver as GPIO
import Zoom as ZoomController
from utils import Location
from collections import deque
import json

conn = db.get_connection()
gps_points = db.GPSData(conn)
commands = db.Commands(conn)
cam_state = db.CameraState(conn)

IO = GPIO.FrontBoardDriver()
Zoom = ZoomController.SoarCameraZoomFocus()

distance_zoom_table = {
    1:1,        
    70:1,
    100:3,
    150:5,      # Example: 150 Meters corresponds to a x5 zoom
    225:15,
    800:30
    # Add as many mappings as needed, making sure they are ordered
}

def normalize_angle(angle):
    return (angle + 180) % 360 - 180

def latlon_to_meters(lat_diff, lon_diff, latitude):
    lat_meters = lat_diff * 111000
    lon_meters = lon_diff * 111000 * math.cos(math.radians(latitude))
    return lat_meters, lon_meters

def gpsDistance(lat1, lon1, lat2, lon2):
	lat1, lon1, lat2, lon2, = map(math.radians, [lat1, lon1, lat2, lon2])
	dlat = lat2 - lat1
	dlon = lon2 - lon1
	a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat1) * math.sin(dlon/2) **2
	c= 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	distance = 6371 * c
	return distance

#   Used for pan speed calculation
last_read = 0
read_time = 0
pan_speed = 0
old_rotation = 0
rotation = 0
servo_rotation = 0
tilt = 0
first_prediction = True
speed_time = 0

trackDistX = 5 # Initiated as non zero to avoid errors 

def calibrationCoordsCal():
    '''
    Saves 15 gps samples and returns the average lat and lon
    '''
    calibrationBufferLAT = np.array([])    # [lats]
    calibrationBufferLON = np.array([])    # [lats]
    while len(calibrationBufferLAT) < 15:  # 5 seconds at 3 Hz to fill the buffer with samples
        time.sleep(0.01)
        if gps_points.new_reading:         # For every new_reading that comes in
            gps_points.new_reading = False
            calibrationBufferLAT = np.append(calibrationBufferLAT, gps_points.latest_gps_data['latitude'])
            calibrationBufferLON = np.append(calibrationBufferLON, gps_points.latest_gps_data['longitude'])
        
    avg_lat = np.average(calibrationBufferLAT)
    avg_lon = np.average(calibrationBufferLON)
    print("Camera Calibration Complete")

    return avg_lat, avg_lon
                
def panCalculations():
    locationToTrack = Location(gps_points.latest_gps_data['latitude'], gps_points.latest_gps_data['longitude'])
    locationOrigin = Location(gps_points.camera_origin['latitude'], gps_points.camera_origin['longitude'])
    print(f"Goal {locationToTrack}; Origin {locationOrigin}; ")
    rotation = -np.degrees(utils.get_angle_between_locations(locationOrigin, locationToTrack) - gps_points.camera_heading_angle)
    print(f"Rotation before normalize {rotation}")
    rotation = normalize_angle(rotation)
    rotation = round(rotation, 1) # Round to 1 decimal place
    print(f"Rotation after normalize {rotation}")
    return rotation

def tiltCalculations():
    global trackDistX
    trackDistX = 1000 * gpsDistance(gps_points.camera_origin['latitude'], gps_points.camera_origin['longitude'],
                                    gps_points.latest_gps_data['latitude'], gps_points.latest_gps_data['longitude'])
    trackDistY = gps_points.camera_vertical_distance
    tiltAngle = np.degrees(math.atan2(trackDistX, trackDistY)) - 90
    tiltAngle = round(tiltAngle, 1) # Round to 1 decimal place
    return tiltAngle

def zoomCalculations():
    global trackDistX
    
    # Find between which 2 mapped values trackDistx fits. This supposes distance_zoom_table is sorted
    lower_distance = max([d for d in distance_zoom_table if d <= trackDistX], default=None)
    upper_distance = min([d for d in distance_zoom_table if d >= trackDistX], default=None)
    
    if lower_distance == upper_distance:
        new_zoom_level = distance_zoom_table[lower_distance]
    else:
        # Interpolate trackDistx based on the distance_zoom_table lookup values
        x0, y0 = lower_distance, distance_zoom_table[lower_distance]
        x1, y1 = upper_distance, distance_zoom_table[upper_distance]
        new_zoom_level = y0 + (trackDistX - x0) * (y1-y0) / (x1-x0)
        new_zoom_level = round(new_zoom_level, 1)
    
    if commands.camera_zoom_value is None or abs(new_zoom_level - commands.camera_zoom_value) >= 0.2:
        Zoom.set_zoom_position(new_zoom_level)
        commands.camera_zoom_value = new_zoom_level
    
def calculate_pan_speed(current_rotation, last_rotation, time_interval):
    # Calculate the difference in angles and divide by the time interval
    angle_difference = normalize_angle(current_rotation - last_rotation)
    return angle_difference / time_interval
        
def get_calibration_from_file():
    try:
        with open("calibration_data", 'r+') as file:
            data = json.load(file)  # Load the JSON data
            gps_points.camera_origin['latitude'] = data.get('originlat')
            gps_points.camera_origin['longitude'] = data.get('originlon')
            gps_points.camera_heading_angle = data.get('heading_angle')
            return data
    except FileNotFoundError:
        print(f"The file calibration_data was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file calibration_data. Ensure it contains valid JSON format.")
        return None
    
def update_calibration_file(key, value):
    data = get_calibration_from_file()
    if data is not None:
        data[key] = value  # Update the dictionary with the new value
        try:
            with open("calibration_data", 'w+') as file:
                json.dump(data, file, indent=4)  # Write the updated dictionary back to the file
                print(f"Updated {key} to {value} in calibration_data.")
        except Exception as e:
            print(f"Error writing to the file calibration_data: {e}")

def main(d):
    last_rotation = None
    last_time = None
    speed_threshold = 1  # Define a threshold for significant speed
    stop_duration_threshold = 5  # Number of seconds to stop recording after panning stops
    stop_timer = 0
    speed_buffer = deque(maxlen=8)  # Buffer to store the last 8 speed measurements
    if get_calibration_from_file(): # Gets the last calibration from a txt file
        print("Calibration data retrieved from file successfully")
    else:
        print("Error retrieving calibration data from file")    
        
    while True:
        time.sleep(0.01)
        IO.setBackPanelLEDs(first = gps_points.gps_fix, second = gps_points.transmission_fix)
        
        if commands.camera_calibrate_origin:        # Calibrate the camera origin coordinate
            commands.camera_calibrate_origin = False
            avg_lat, avg_lon = calibrationCoordsCal()
            gps_points.camera_origin['latitude'] = avg_lat
            gps_points.camera_origin['longitude'] = avg_lon
            print(f"Camera Origin {gps_points.camera_origin['latitude']}, {gps_points.camera_origin['longitude']} Calibrated")
            update_calibration_file('originlat', avg_lat)
            update_calibration_file('originlon', avg_lon)
            get_calibration_from_file() 
            
        elif commands.camera_calibrate_heading:       # Calibrate the camera heading coordinate
            commands.camera_calibrate_heading = False
            avg_lat, avg_lon = calibrationCoordsCal()
            gps_points.camera_heading_coords['latitude'] = avg_lat
            gps_points.camera_heading_coords['longitude'] = avg_lon
            cam_position = Location(gps_points.camera_origin['latitude'], gps_points.camera_origin['longitude'])
            cam_heading = Location(gps_points.camera_heading_coords['latitude'], gps_points.camera_heading_coords['longitude'])
            gps_points.camera_heading_angle = utils.get_angle_between_locations(cam_position, cam_heading)
            update_calibration_file('heading_angle', gps_points.camera_heading_angle)
            get_calibration_from_file()
            
            print(f"Camera Heading {gps_points.camera_heading_coords['latitude']}, {gps_points.camera_heading_coords['longitude']}")
            print(f"Camera Heading Angle {gps_points.camera_heading_angle}")
            print("Camera Heading Calibration Complete")
        
        if commands.tracking_enabled:
            if gps_points.new_reading:
                gps_points.new_reading = False
                panAngle = panCalculations()
                tiltAngle = tiltCalculations()
                zoomCalculations()
                IO.setAngles(pan = panAngle, tilt = tiltAngle + gps_points.tilt_offset)
                print(f"Pan: {panAngle} ; Tilt: {tiltAngle + gps_points.tilt_offset}")
        
                if last_rotation is not None and last_time is not None and cam_state.enable_auto_recording:
                    # Calculate the time interval
                    current_time = time.time()
                    time_interval = current_time - last_time
                    
                    # Calculate pan speed
                    pan_speed = calculate_pan_speed(panAngle, last_rotation, time_interval)
                    speed_buffer.append(pan_speed)
                    if len(speed_buffer) > 1:
                        average_speed = sum(speed_buffer) / len(speed_buffer)
                    else:
                        average_speed = pan_speed
                    
                    # Check if speed exceeds the threshold
                    if average_speed > speed_threshold:
                        # Start recording if not already started
                        if not cam_state.start_recording:
                            cam_state.start_recording = True
                            print("Start recording due to increased pan speed")
                        stop_timer = 0  # Reset stop timer
                    elif cam_state.start_recording:
                        # Increment stop timer if already recording
                        stop_timer += time_interval
                        if stop_timer >= stop_duration_threshold:
                            cam_state.start_recording = False
                            print("Stop recording due to lack of pan movement")
                    
                    # Update last rotation and time
                    last_rotation = panAngle
                    last_time = current_time
        else:
            IO.setAngles(pan = 0, tilt= 0)
            #Zoom.set_zoom_position(25)
            if cam_state.start_recording:
                cam_state.start_recording = False
                print("Stop recording due to tracking disabled")
            
                        
if __name__ == "__main__":
    main({"stop": False}) 