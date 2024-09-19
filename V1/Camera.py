import threading
import time
import db
import subprocess
import time

# Function to start recording
def start_recording(rtsp_url, output_file):
    # Command to start recording
    command = [
        'ffmpeg',
        '-i', rtsp_url,
        '-c:v', 'copy',  # Copy video stream to maintain quality
        '-y',  # Overwrite output file if it exists
        output_file
    ]
    
    # Start ffmpeg process in the background
    ffmpeg_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Recording started. Output file: {output_file}")
    return ffmpeg_process

# Function to stop recording
def stop_recording(ffmpeg_process):
    # Terminate ffmpeg process
    ffmpeg_process.terminate()
    try:
        ffmpeg_process.wait(timeout=2)
        print("Recording stopped.")
    except subprocess.TimeoutExpired:
        ffmpeg_process.kill()
        print("Recording forcefully stopped.")


class Cam():

	def __init__(self, q_frame = None):
		self.running = False  
		self.video_file = ''
		conn = db.get_connection()
		self.camera_state = db.CameraState(conn)
		self.commands = db.Commands(conn)
		self.gps = db.GPSData(conn)
  
		self.camera_state.is_recording = False
		self.camera_state.start_recording = False

		self.rtsp_url = 'rtsp://admin:IDMind2000!@192.168.1.68'
		#self.rtsp_url = 'udp://127.0.0.1:1234'


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

	def worker(self):
		self.running = True

		while(self.run):
			time.sleep(0.02)
   
			if self.camera_state.start_recording and not self.camera_state.is_recording: # START RECORDING
				timeStamp = time.strftime('%H%M%S', time.localtime())
				self.camera_state.timeStamp = timeStamp
				self.camera_state.is_recording = True
				print("Start recording with timeStamp {}".format(timeStamp))
				self.video_file = f"/home/IDMind/Documents/V1/videos/{timeStamp}.mp4"
				self.recording_process = start_recording(self.rtsp_url, self.video_file)
    
			if self.camera_state.is_recording and not self.camera_state.start_recording:	# When we stop recording, save the first 300 frames from the FIFO buffer to the video file and then the remaining video frames
				self.camera_state.is_recording = False
				stop_recording(self.recording_process)
				print("Recording Session Finished")
   
		self.running = False

def main(d):
    c = Cam()

    print("Starting cam")
    c.start()
    time.sleep(2)         # should be implemented with queue/signals but good enough for testing
    print("Cam is operational")
    
    #recording_process = start_recording(c.rtsp_url, "/home/IDMind/Documents/V1/videos/teste.mp4" )
    #print("RECORDING")
 
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
