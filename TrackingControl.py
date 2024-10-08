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

lower_distance = 0
upper_distance = 0


distance_zoom_table = {
    1:1,
    15:1,
    25:2,
    50:4,
    75:4.5,
    100:5,
    120:7,
    140:9,
    160:11,
    215:13,
    300:15
    # Add as many mappings as needed, making sure they are ordered
}

'''
distance_zoom_table = {
    0:0,
    30:0,
    400:15
}
   ''' 



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

trackDistX = 1 # Initiated as non zero just to avoid errors 

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
    
    return avg_lat, avg_lon
                
def panCalculations():
    locationToTrack = Location(gps_points.latest_gps_data['latitude'], gps_points.latest_gps_data['longitude'])
    locationOrigin = Location(gps_points.camera_origin['latitude'], gps_points.camera_origin['longitude'])
    rotation = -np.degrees(utils.get_angle_between_locations(locationOrigin, locationToTrack) - gps_points.camera_heading_angle)
    rotation = normalize_angle(rotation)
    rotation = round(rotation, 1) # Round to 1 decimal place
    return rotation

def tiltCalculations():
    global trackDistX
    trackDistX = 1000 * gpsDistance(gps_points.camera_origin['latitude'], gps_points.camera_origin['longitude'],
                                    gps_points.latest_gps_data['latitude'], gps_points.latest_gps_data['longitude'])
    trackDistY = gps_points.camera_vertical_distance
    tiltAngle = np.degrees(math.atan2(trackDistX, trackDistY)) - 90
    tiltAngle = round(tiltAngle, 1) # Round to 1 decimal place
    return -tiltAngle

def zoomCalculations():
    global trackDistX
    
    # Find between which 2 mapped values trackDistx fits. This assumes distance_zoom_table is sorted
    lower_distance = max([d for d in distance_zoom_table if d <= trackDistX], default=1)
    upper_distance = min([d for d in distance_zoom_table if d >= trackDistX], default=15)
    
    if lower_distance == upper_distance:
        new_zoom_level = distance_zoom_table[lower_distance]
    else:
        # Interpolate trackDistx based on the distance_zoom_table lookup values
        x0, y0 = lower_distance, distance_zoom_table[lower_distance]
        x1, y1 = upper_distance, distance_zoom_table[upper_distance]
        new_zoom_level = y0 + (trackDistX - x0) * (y1-y0) / (x1-x0)
        new_zoom_level = round(new_zoom_level*1.25, 3)
    
    if commands.camera_zoom_value is None or abs(new_zoom_level - commands.camera_zoom_value) >= 0.001:
        Zoom.set_zoom_position(new_zoom_level)
        commands.camera_zoom_value = new_zoom_level
    
       
def get_calibration_from_file():
    try:
        with open("calibration_data", 'r+') as file:
            data = json.load(file)  # Load the JSON data
            gps_points.camera_origin = {
                                            "latitude": data.get('originlat'),
                                            "longitude": data.get('originlon')
                                        }
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

panBuffer = deque(maxlen=3)
timeBuffer = deque(maxlen=3)

'''
Ignorar tracking se distancia < 50m
'''


def main(d):
    Zoom = ZoomController.SoarCameraZoomFocus()
    
    panAngle = None
    last_read_time = None
    panSpeed = 0
    
    commands.tracking_enabled = False
    
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
            print(avg_lat)
            print(avg_lon)
            gps_points.camera_origin = {
                                        'latitude': avg_lat,
                                        'longitude': avg_lon
                                        }
            print(f"Camera Origin {gps_points.camera_origin['latitude']}, {gps_points.camera_origin['longitude']} Calibrated")
            update_calibration_file('originlat', avg_lat)
            update_calibration_file('originlon', avg_lon)
            get_calibration_from_file() 
            
        elif commands.camera_calibrate_heading:       # Calibrate the camera heading coordinate
            commands.camera_calibrate_heading = False
            avg_lat, avg_lon = calibrationCoordsCal()
            gps_points.camera_heading_coords = {
                                        'latitude': avg_lat,
                                        'longitude': avg_lon
                                        }
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
                last_read_time = time.time()
                panAngle = panCalculations()
                tiltAngle = tiltCalculations()
                zoomCalculations()
            
                # Before appending the new value check if it follows the previous Trend
                # If it does, append it to the array and continue as is
                # If not, sudden change of direction or stop has occured -> clear buffer and start filling
                if tendency(panAngle, panBuffer):
                    panBuffer.append(panAngle)
                    timeBuffer.append(last_read_time)   
                    panSpeed = average_pan_speed(panBuffer, timeBuffer)
                else:
                    panBuffer.clear()
                    timeBuffer.clear()
                    panBuffer.append(panAngle)
                    timeBuffer.append(last_read_time)   
                    panSpeed = average_pan_speed(panBuffer, timeBuffer)
                    
                print(f"Current Pan Speed is {panSpeed}")
                
                if trackDistX >= 15: # Only track if target is away from the camera
                    speed_control_mode_threshold = 0.6
                    if abs(panSpeed) < speed_control_mode_threshold:
                        ''' Position Control for accuracy at low speeds  '''
                        IO.setPanPositionControl()
                        IO.setAngles(pan = panAngle, tilt = tiltAngle + gps_points.tilt_offset)
                        print(f"Position Control        Pan: {panAngle} ; Tilt: {tiltAngle + gps_points.tilt_offset}")
                    elif abs(panSpeed) >= speed_control_mode_threshold and abs(panSpeed) <= 15:
                        ''' Velocity Control for a smooth pan movement at considerable speeds '''
                        IO.setPanVelocityControl()
                        IO.setPanGoalVelocity(panSpeed)
                        IO.setTiltAngle(tilt = tiltAngle + gps_points.tilt_offset)
                        print(f"Velocity Control        PanSpeed = {panSpeed} ; Tilt: {tiltAngle + gps_points.tilt_offset}")
                else:
                    print("Tracking is enabled but target is too close to track")
                    
            else:   # No new readings, make sure pan doesnt keep rotating at constant speed
                if time.time() - last_read_time > 3:
                    IO.setPanPositionControl()
                    IO.setAngles(pan = panAngle, tilt = tiltAngle + gps_points.tilt_offset)
                
        else:   # If not tracking
            IO.setPanPositionControl()
            IO.setPanGoalVelocity(0)
            IO.setAngles(pan = 0, tilt= 5)
            Zoom.set_zoom_position(2)
            panBuffer.clear()
            timeBuffer.clear()
            
def average_pan_speed(pan_values, timestamps):
    if len(pan_values) != len(timestamps):
        raise ValueError("PAN values and timestamps arrays must be of the same length.")
    
    if len(pan_values) < 2:
        return 0
    
    total_distance = 0
    total_time = 0
    
    for i in range(1, len(pan_values)):
        distance = pan_values[i] - pan_values[i - 1]
        time = timestamps[i] - timestamps[i - 1]
        
        if time <= 0:
            raise ValueError("Timestamps must be in increasing order and have positive intervals.")
        
        total_distance += distance
        total_time += time
    
    average_speed = total_distance / total_time
    return average_speed

def tendency(value, array):
    '''
    Checks if a new value to be inserted follows the general tendency of the array
    '''
    
    if len(array) < 2:  # too little values, assume no trend and return True to immediately keep appending the array 
        return True
    
    trend = 0
    diffs = [array[i] - array[i-1] for i in range(1, len(array))]
    if all(d > 0 for d in diffs):
        trend = 1     # there is a tendency (sign doesnt matter) so return True to keep appending
    elif all(d < 0 for d in diffs):
        trend = -1    # No clear trend in values, return False to immediately clear the array	
    last_val = array[-1]
    
    if(trend == 1 and value < last_val) or (trend == -1 and value > last_val):    # New val does not follow trend
        return False
    
    return True # this means the new value follows the trend --> return True
          
if __name__ == "__main__":
    main({"stop": False}) 
