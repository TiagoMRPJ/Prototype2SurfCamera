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
        
        ready = False
        while True:
            
            if not self.commands.tracking_enabled and not ready:
                ready = True
                            
            if self.commands.tracking_enabled and ready:
                coordinates = self.get_coordinates()
                lastt = 0
                for coordinate in coordinates:
                    lat, lon, tstamp = coordinate.split(',')
                    if lastt == 0:
                        time.sleep(0.4)
                    else:
                        time.sleep(float(tstamp) - float(lastt))
                    position = {"latitude": float(lat), "longitude": float(lon)}
                    self.gps_points.latest_gps_data = position
                    self.gps_points.new_reading = True
                    self.gps_points.last_gps_time = float(tstamp)
                    lastt = float(tstamp)
                ready = False
                print("Simulation Cycle Complete")
                
            else:
                time.sleep(1)
                         
def main(d):
    fakegps = FakeTracker('/home/IDMind/Documents/V1/gps_simulator/fakegpsdata.txt')
    fakegps.worker()
    
if __name__ == "__main__":
    fakegps = FakeTracker('fakegpsdata.txt')
    fakegps.worker()
