import db

conn = db.get_connection()
gps_points = db.GPSData(conn)
camera_state = db.CameraState(conn)

def main(d):
    while True:
        time.sleep(0.25)
    