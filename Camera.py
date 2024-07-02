import threading
import cv2
import time
import db
from collections import deque
import numpy as np

class Cam():

	def __init__(self, q_frame = None):
		self.running = False
		self.is_recording = False	  
		self.fps = 0
		self.q_frame = q_frame
		self.q_len = 10
		self.cam_text = ""
		self.video_file = ''
		conn = db.get_connection()
		self.camera_state = db.CameraState(conn)
		self.commands = db.Commands(conn)
		self.camera_state.start_recording = False
		self.frame_buffer = deque(maxlen=300)  # FIFO buffer for the most recent 300 frames

	def start(self, nr=0):
		self.run = True
		self.capture_thread = None
		self.nr = nr
		self.capture_thread = threading.Thread(target=self.worker)
		self.capture_thread.start()

	def stop(self): 
		self.run = False		
		try:
			self.capture_thread.join()
		except:
			pass
		
		while self.running:
			time.sleep(0.01)

	def set(self, param=None, value=None):
		self.capture.set(param, value)

	def get(self, param=None):
		self.capture.get(param)

	def worker(self):
		self.running = True
		self.capture = cv2.VideoCapture("rtsp://admin:IDMind2000!@192.168.1.68")
		print('Camera Parameters', self.capture.get(0), self.capture.get(1), self.capture.get(2), self.capture.get(3), self.capture.get(4), self.capture.get(5))
		self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
		self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
		self.capture.set(cv2.CAP_PROP_FPS,30)
		self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
		#self.capture.set(cv2.CAP_PROP_MODE, 3)
		self.frame_width = int(self.capture.get(3))
		self.frame_height = int(self.capture.get(4))
		print("Size", self.frame_width, self.frame_height)
		start = time.time()
		while(self.run):
			ret_video = {}
			end = time.time()
			new_frame, img = self.capture.read()

			if not self.is_recording:  		# Append recent frame to the 300 FIFO buffer while not recording to keep store of the last ~10 seconds
				self.frame_buffer.append(img)

			if self.camera_state.start_recording and not self.is_recording: # If we start recording, create video buffer and create video file
				self.is_recording = True
				print("Start recording with timeStamp {}".format(time.time()))
				self.video_file = cv2.VideoWriter(str(int(time.time()))+'.avi', 0, cv2.VideoWriter_fourcc(*'MJPG'), 25, (2560,1440))
				self.videobuffer = []
			if self.is_recording and not self.camera_state.start_recording:	# When we stop recording, save the first 300 frames from the FIFO buffer to the video file and then the remaining video frames
				self.is_recording = False

				for f in self.frame_buffer:
					self.video_file.write(f)
				for f in self.videobuffer:
					self.video_file.write(f)
     
				self.video_file.release()
				new_frame, img = self.capture.read()
				print("Recording Session Finished")
			
			if self.is_recording and new_frame:
				self.videobuffer.append(img)
    			#self.videobuffer = np.append(self.videobuffer,  img, axis=None)
				#self.video_file.write(img)

			elapsed = end-start
			if elapsed > 0:
				self.fps = 1 / (elapsed)
				#print(self.fps)
			else:
				self.fps = 0
			start = end
     
			if not self.is_recording:
				resized_img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA)
				frame = cv2.imencode('.jpg', resized_img)[1].tobytes() 
				self.camera_state.image = (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
		
		self.capture.release()
		self.running = False

def main(d):
	c = Cam()

	print("Starting cam")
	c.start()

	print("Waiting for camera")
	while c.fps == 0:
		time.sleep(0.1) # should be implemented with queue/signals but good enough for testing
	print("Cam is operational")
 
	try:
		while True:
			time.sleep(0.01)
			if not c.running:
					break
	except KeyboardInterrupt:
		pass

	print("Stopping camera")
	c.stop()
 
if __name__ == "__main__":
    main({"stop":False})