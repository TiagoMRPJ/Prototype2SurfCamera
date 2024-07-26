import math
import random

# Constants
START_LAT = 38.7301223211142
START_LON = -9.47591882827879
SPEED_M_S = 2  # meters per second
TIME_INTERVAL = 1  # seconds between points
EARTH_RADIUS = 6371000  # meters (mean radius of Earth)



def lon_offset(distance_m, lat):
    """Calculate the longitude offset in degrees given a distance and latitude."""
    return (distance_m / (math.pi * EARTH_RADIUS * math.cos(math.radians(lat)) / 180.0))

# Initialize values
lat = START_LAT
lon = START_LON
distance_traveled = 0

# Generate coordinates
coordinates = []
for _ in range(100):  # Number of points
    coordinates.append(f"{lat},{lon}")
    distance_traveled += SPEED_M_S * TIME_INTERVAL
    lon += lon_offset(SPEED_M_S * random.uniform(0.5,1.5), lat)

# Write to file
with open(r"fakegpsdata.txt", "w+") as file:
    file.write("\n".join(coordinates))