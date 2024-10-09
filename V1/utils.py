#! /usr/bin/env python3
import numpy as np
import math

R = 6371 * 1000 # METERS

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
	return round(brng, 2)


def get_distance_between_locations(loc0, loc1):
		'''
		Returns distance in same unit as R (in this case meters)
		'''
		latA = np.radians(loc0.latitude)
		lonA = np.radians(loc0.longitude)
		latB = np.radians(loc1.latitude)
		lonB = np.radians(loc1.longitude)
		dist = R * np.arccos(min(max(np.sin(latA) * np.sin(latB) + np.cos(latA) * np.cos(latB) * np.cos(lonA-lonB) , -1), 1))
		return dist

def linterpol(value, x1, x2, y1, y2):
	return y1 + (value - x1) * (y2 - y1) / (x2 - x1)

def normalize(value, range_min, range_max):
	return (value - range_min) / (range_max - range_min)
	

class emafilter:
	def __init__(self, alpha = 0.2):
		self.new_angle_rad = 0
		self.ema_sin = 0
		self.ema_cos = 0
		self.ALPHA = alpha
		
	def exponential_moving_average(self, new_angle_deg):
		self.new_angle_rad = new_angle_deg * math.pi / 180.0
		self.ema_sin = (1 - self.ALPHA) * self.ema_sin + self.ALPHA * math.sin(self.new_angle_rad)
		self.ema_cos = (1 - self.ALPHA) * self.ema_cos + self.ALPHA * math.cos(self.new_angle_rad)
		self.mean_angle_rad = math.atan2(self.ema_sin, self.ema_cos)

		return (self.mean_angle_rad * 180.0 / math.pi + 360.0) % 360.0


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