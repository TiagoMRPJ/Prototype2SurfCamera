import serial
import serial.tools.list_ports
import time
import db
import threading
import os


'''
Process responsible for handling the Serial Communication with the Radio receiver to continuously update the latest GPS data.
While recording, the data is also saved to log files.
'''


SERIAL_PORT = ""
while SERIAL_PORT == "":
	ports = list(serial.tools.list_ports.comports())
	for p in ports:
		if p.description and "CP2102N" in p.description:
			SERIAL_PORT = p.device
			break

  
ser = serial.Serial(SERIAL_PORT, baudrate=115200)#, timeout= None, xonxoff=False, rtscts=False, dsrdtr=False)
ser.flushInput()
ser.flushOutput()
receiveTime = 0
lastReceiveTime = 0
lastLat = 0
lastLon = 0
sats = 0
rssi = 0
distance = 0

newRead = False

class ReadLine:
	def __init__(self, s):
		self.buf = bytearray()
		self.s = s

	def readline(self):
		i = self.buf.find(b"\n")
		if i >= 0:
			r = self.buf[:i+1]
			self.buf = self.buf[i+1:]
			return r
		while True:
			i = max(1, min(2048, self.s.in_waiting))
			data = self.s.read(i)
			i = data.find(b"\n")
			if i >= 0:
				r = self.buf + data[:i+1]
				self.buf[0:] = data[i+1:]
				return r
			else:
				self.buf.extend(data)
				
rl = ReadLine(ser)

def receive():
	if ser.in_waiting > 0:
		try:
			line = rl.readline().decode().rstrip()
			if len(line.split(',')) != 4:
				pass
			else:
				decode(line)
		except:
			print('.')
   
def decode(line):
	global receiveTime, lastReceiveTime, interval, newRead
	global lastLat, lastLon, lastAlt, distance, sats, rssi
	if len(line.split(',')) == 4:
		data = line.split(',')
		lat = float(data[0]) / 10000000
		lon = float(data[1]) / 10000000
		sats = int(data[2])
		rssi = int(data[3])
		if int(lat) == 38 and int(lon) == -9: 
			lastLat = lat
			lastLon = lon
		newRead = True
	else:
		print('ERROR: ',line)
  
def Rx_thread():
	while True:
		receive()
		time.sleep(0.05)
  
def main(d):
	global lastLat, lastLon, newRead, distance
	conn = db.get_connection()
	gps_points = db.GPSData(conn)
	camera_state = db.CameraState(conn)
	webapp = db.WebApp(conn)
	gps_points.gps_fix = False
	gps_points.transmission_fix = False
	time_new_read = time.time()
 
	cur_dir = ""	# used for gps logging with appropriate file path and name
	lastwavenr = -1
		
	rec_Thread = threading.Thread(target=Rx_thread)
	rec_Thread.daemon = True                        #  so that it stops when the main one stops
	rec_Thread.start()
	
	try:
		while True:
			time.sleep(0.05)
			if time.time() - time_new_read >= 3:	# If transmission stops for over 3 seconds turn off both leds
				gps_points.transmission_fix = False # Turn OFF the LED indicating transmission
				gps_points.gps_fix = False 			# Just so that both LEDS turn OFF 
			else:
				gps_points.transmission_fix = True	
	
			if newRead:
				time_new_read = time.time()
				position = {"latitude": float(lastLat), "longitude": float(lastLon)}
				gps_points.latest_gps_data = position
				gps_points.last_gps_time = time_new_read
				#print(f"{gps_points.latest_gps_data['latitude']}, {gps_points.latest_gps_data['longitude']}, {sats}, {rssi}")
	
				if sats >= 5:					# If the tracker has a fix with more than 5 sattelites turn ON the led indicating gps fix
					gps_points.gps_fix = True
				else:
					gps_points.gps_fix = False  # If there are little sattelites fixed, turn off the led
		
				gps_points.new_reading = True
				newRead = False
	
				if not camera_state.is_recording: 
						
					if webapp.SessionID != "-1":
						new_dir = f"/home/IDMind/Documents/V1/gps_logs/{webapp.SessionID}"
					else:
						new_dir = f"/home/IDMind/Documents/V1/gps_logs/other"
			
					if new_dir != cur_dir:
						cur_dir = new_dir
						create_directory_if_not_exists(cur_dir)

					filegpslog = open(os.path.join(cur_dir, f"{camera_state.wave_nr}.txt"), "w")
		   
				if camera_state.is_recording and True:	# If the Camera is recording, also log the gps coordinates in a file with the same timestamp
						filegpslog.write(f"{lastLat}, {lastLon}, {time.time()}\n")
			
	except KeyboardInterrupt:
		rec_Thread.join()
		pass

def create_directory_if_not_exists(directory_path):
	os.makedirs(directory_path, exist_ok=True)
	#print(f"Directory '{directory_path}' is ready.")

if __name__ == "__main__":
	main({"stop": False})
	
