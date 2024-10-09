#! /usr/bin/python
import time
import sys

import Camera
import RadioGps
import TrackingControl
import WebServer
sys.path.append('/home/IDMind/Documents/V1/gps_simulator')
#import GPSSIMULATOR

from multiprocessing import Process, Manager
import redis
from db import RedisClient

r = redis.Redis()
client = RedisClient(r)

PERSISTENT_FILENAME = "/home/IDMind/Documents/V1/db.txt"

PROCESSES = [
    Camera,
    #GPSSIMULATOR,
    RadioGps,
    TrackingControl,
    WebServer
]

if __name__ == '__main__':
    manager = Manager()
    client.set_initial("stop_surf", False)
    d = manager.dict()
    d["stop"] = False
    client.load(PERSISTENT_FILENAME)
    
    process_list = []
    for p in PROCESSES:
        process_list.append(Process(target=p.main, args=(d,)))
        time.sleep(0.5)
    for p in process_list:
        p.start()
        time.sleep(0.5)
