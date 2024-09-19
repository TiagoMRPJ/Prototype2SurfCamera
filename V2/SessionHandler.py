import os
from os import listdir
from os.path import isfile, join
from datetime import datetime
import sys
sys.path.append('/home/IDMind/Documents/V1/')
import utils

'''
Provides the functions needed for calculating the cumulative distance surfed in a session, the maximum velocity reached and how many waves were surfed, 
through the GPS logs of the session.

Example:
session = '112'
cumulative_distance, top_speed, wave_count = get_gps_stats(session)

'''


def get_session_directory(sessionID, folder):
    return f"/home/IDMind/Documents/V1/{folder}/{sessionID}"

def create_video_directory(ID):
    dir_path = get_session_directory(ID , "videos")
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
        print(f"Directory for {ID} videos created succesfully!")
    else:
        print(f"Directory for {ID} videos already exists! ")
        
def create_gps_logs_directory(ID):
    dir_path = get_session_directory(ID , "gps_logs")
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
        print(f"Directory for {ID} gpslogs created succesfully!")
    else:
        print(f"Directory for {ID} gpslogs already exists! ")
        

def create_session_directories(sessionID):
    create_video_directory(sessionID)
    create_gps_logs_directory(sessionID)
    
        
def get_wave_count(sessionID):
    # Takes the sessionID to count how many wave videos there are
    mypath = get_session_directory(sessionID , "gps_logs")
    waves = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    return len(waves) 

def calculate_distance_and_speed(file_path):
    # Takes the path to a specific GPS_LOG file to calculate distance and speed 
    total_distance = 0.0
    max_speed = 0.0
    prev_lat, prev_lon, prev_time = None, None, None

    with open(file_path, 'r') as file:
        for line in file:
            lat, lon, timestamp = line.strip().split(',')
            lat, lon = float(lat), float(lon)
            current_time = float(timestamp) 
            if prev_lat is not None and prev_lon is not None:
                prev_loc = utils.Location(prev_lat, prev_lon)
                loc = utils.Location(lat, lon)
                # Calculate distance between two points
                distance = utils.get_distance_between_locations(prev_loc, loc)
                total_distance += distance
                
                # Calculate time difference in hours
                time_diff = (current_time - prev_time)
                if time_diff > 0:
                    # Calculate speed (distance / time)
                    speed = distance / time_diff
                    max_speed = max(max_speed, speed)
            
            # Update previous values
            prev_lat, prev_lon, prev_time = lat, lon, current_time

    return total_distance, max_speed

def get_gps_stats(sessionID):
    '''
    After a session, this returns the cumulative distance surfed by the session, the maximum speed reached and in each wave, and finally the wave count
    Takes sessionID as str
    Returns cumulative distance of the session in km, max speed in km/h 
    '''
    mypath = get_session_directory(sessionID , "gps_logs")
    waves = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    cumulative_dist = 0
    max_speed = 0
    waveid_max_speed = ''
    for wave in waves:
        d, s = calculate_distance_and_speed(f'/home/IDMind/Documents/V1/gps_logs/{sessionID}/{wave}')
        cumulative_dist += d
        if s > max_speed:
            max_speed = s
            waveid_max_speed = wave

    return round(cumulative_dist/1000, 2), round(max_speed*3.6, 1), waveid_max_speed, get_wave_count(sessionID) 

session = 'demo'
dist, speed, wave, count = get_gps_stats(session)
print(f"Surfed a cumulative distance of {dist} km")
print(f"Reached a MaxSpeed of {speed} km/h on Wave {wave}")
print(f"WaveCount: {count}")
