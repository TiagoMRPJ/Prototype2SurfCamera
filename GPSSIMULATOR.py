import threading
import time
import math
from utils import Location
import random

import db

class FakeTracker:
    def __init__(self, filename = None):
        try:
            self.gps_file = filename
        except:
            raise Exception("NO FILENAME PROVIDED")
        
        conn = db.get_connection()
        self.gps_points = db.GPSData(conn) 
        self.camera_state = db.CameraState(conn)
        self.commands = db.Commands(conn)
        
        
    def get_coordinates(self):
        with open(self.gps_file, 'r') as file:
            coordinates = file.readlines()
        coordinates = [line.strip() for line in coordinates]
        return coordinates
    
    def worker(self):
        while True:
            if self.commands.tracking_enabled:
                coordinates = self.get_coordinates()
                for coordinate in coordinates:
                    sleept = 0.4 + random.uniform(-0.1, 0.25)
                    time.sleep(sleept)
                    lat, lon = coordinate.split(',')
                    position = {"latitude": float(lat), "longitude": float(lon)}
                    self.gps_points.latest_gps_data = position
                    self.gps_points.new_reading = True
            else:
                time.sleep(1)
                         
def main(d):
    fakegps = FakeTracker('fakegpsdata.txt')
    fakegps.worker()
    
if __name__ == "__main__":
    fakegps = FakeTracker('fakegpsdata.txt')
    fakegps.worker()
