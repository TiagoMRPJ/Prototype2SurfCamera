#! /usr/bin/env python3
import numpy as np
import math

R = 6371 * 1000


class Location:
    def __init__(self, lat, lon, alt=0):
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt

def gps_to_cartesian(loc):
    lat = np.radians(loc.latitude)
    lon = np.radians(loc.longitude)
    x = R * np.cos(lat) * np.cos(lon)
    y = R * np.cos(lat) * np.sin(lon)
    z = R * np.sin(lat)
    return x, y, z


def get_angle_between_locations(l1, l2):
	if get_distance_between_locations(l1, l2) < 1:
		return 0
	lat1 = np.radians(l1.latitude)
	long1 = np.radians(l1.longitude)
	lat2 = np.radians(l2.latitude)
	long2 = np.radians(l2.longitude)
	dLon = long2 - long1
	y = np.sin(dLon) * np.cos(lat2)
	x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dLon)
	y *= -1
	x *= 1
	brng = np.arctan2(y, x)
	return brng


def get_distance_between_locations(loc0, loc1):
    latA = np.radians(loc0.latitude)
    lonA = np.radians(loc0.longitude)
    latB = np.radians(loc1.latitude)
    lonB = np.radians(loc1.longitude)
    return R * np.arccos(np.sin(latA) * np.sin(latB) + np.cos(latA) * np.cos(latB) * np.cos(lonA-lonB))

def linterpol(value, x1, x2, y1, y2):
    return y1 + (value - x1) * (y2 - y1) / (x2 - x1)


def normalize(value, range_min, range_max):
    return (value - range_min) / (range_max - range_min)
    
ALPHA = 0.25
def exponential_moving_average(new_angle_deg, ema_sin, ema_cos):
	new_angle_rad = new_angle_deg * math.pi / 180.0
	ema_sin = (1 - ALPHA) * ema_sin + ALPHA * math.sin(new_angle_rad)
	ema_cos = (1 - ALPHA) * ema_cos + ALPHA * math.cos(new_angle_rad)
	mean_angle_rad = math.atan2(ema_sin, ema_cos)

	return (mean_angle_rad * 180.0 / math.pi + 360.0) % 360.0
"""
def get_distance_between_locations(loc0, loc1):
    latA = np.radians(loc0["latitude"])
    lonA = np.radians(loc0["longitude"])
    latB = np.radians(loc1["latitude"])
    lonB = np.radians(loc1["longitude"])
    distance = 2*R*np.arcsin(math.sqrt(np.sin((latB-latA)/2)**2+np.cos(latA)*np.cos(latB)*np.sin((lonB-lonA)/2)**2))
    return distance



def get_angle_between_locations(home, orientation, location):
	print("home:", home, "orientation", orientation, "location", location)
	prevTheta = 0
	a = get_distance_between_locations(home, location)
	b = get_distance_between_locations(home, orientation)
	c = get_distance_between_locations(orientation, location)
	try:
		preAng = ((np.cos(c)-np.cos(a)*np.cos(b))/(np.sin(a)*np.sin(b))) % 1
		print(preAng)
	except:
		print("-__-")
	if preAng < 0:
		theta = -np.degrees(np.arccos(preAng))
		print("Negative")
	else:
		theta = np.degrees(np.arccos(preAng))
		print("Positive")
	if abs(theta-prevTheta)>1:
		prevTheta = theta
		return theta
	else:
		return prevTheta
"""