import threading
import time
import db
import cv2
from collections import deque
import numpy as np
import subprocess
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Function to start recording live stream immediately
def start_recording(rtsp_url, output_file):
    command = [
        'ffmpeg',
        '-i', rtsp_url,
        '-c:v', 'copy',
        '-y',
        output_file
    ]
    #subprocess.run(command)
    ffmpeg_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Recording started. Output file: {output_file}")
    return ffmpeg_process

# Function to stop recording live stream
def stop_recording(ffmpeg_process):
    ffmpeg_process.terminate()
    try:
        ffmpeg_process.wait(timeout=2)
        print("Recording stopped.")
    except subprocess.TimeoutExpired:
        ffmpeg_process.kill()
        print("Recording forcefully stopped.")

# Function to save the buffer frames into a vid file and concatenate buffer video with the ffmpeg recorded video
def save_buffer_and_concatenate_videos(buffer, buffer_file, main_file, output): # MoviePy Solution Async
    def savebuffer_and_concatenate():
        height, width, _ = buffer[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(buffer_file, fourcc, 30, (width, height))
        
        for frame in buffer: 
            out.write(frame)
        
        buffer.clear()  # Clear the buffer after processing
        out.release()
        print(f"Buffered frames saved to: {buffer_file}")
    
    
        try:
            clip_1 = VideoFileClip(buffer_file)
            clip_2 = VideoFileClip(main_file)
            final_clip = concatenate_videoclips([clip_1, clip_2])
            final_clip.write_videofile(output)
        except:
            pass
        

    # Create a thread to run the concatenation
    concatenation_thread = threading.Thread(target=savebuffer_and_concatenate)
    concatenation_thread.start()

    # You can return the thread if you want to monitor its status
    return concatenation_thread

class Cam:

    def __init__(self, q_frame=None, buffer_seconds=5):
        self.running = False  
        self.video_file = ''
        self.buffer_file = ''
        conn = db.get_connection()
        self.camera_state = db.CameraState(conn)
        self.commands = db.Commands(conn)
        self.camera_state.is_recording = False
        self.camera_state.start_recording = False

        #self.rtsp_url = 'rtsp://admin:IDMind2000!@192.168.1.68'
        self.rtsp_url = 'udp://127.0.0.1:1234'
        
        # Buffer to hold the last 'buffer_seconds' of frames
        self.buffer_seconds = buffer_seconds
        self.fps = 30 
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)
        self.concat_thread = None  # Initialize the thread attribute


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

        # Open the video stream
        cap = cv2.VideoCapture(self.rtsp_url)

        while self.run:
            time.sleep(0.01)
            
            ret, frame = cap.read()
            if not ret:
                continue
        
            if not self.camera_state.is_recording: # While not recording, keep updating the latest footage on the buffer
                if self.concat_thread is None: # If the thread still doesnt exist
                    # Add the frame to the buffer
                    self.frame_buffer.append(frame)
                    print("APPENDED BECAUSE THREAD IS NONE")
                elif not self.concat_thread.is_alive(): # If thread exists but isnt alive
                    print("APPENDED BECAUSE THREAD IS NOT ALIVE")
                    self.frame_buffer.append(frame)
                else:
                    #self.concateni
                    print("NOT APPENDING BECAUSE THREAD IS RUNNING")
            
            if self.camera_state.start_recording and not self.camera_state.is_recording:
                # Start immediate recording with ffmpeg
                self.camera_state.is_recording = True
                timeStamp = time.strftime('%H%M%S', time.localtime())
                self.camera_state.timeStamp = timeStamp
                print(f"Start recording with timeStamp {timeStamp}")
                self.video_file = f"videos/{timeStamp}_live.mp4"
                self.recording_process = start_recording(self.rtsp_url, self.video_file)
            
            if self.camera_state.is_recording and not self.camera_state.start_recording:
                # Stop recording
                self.camera_state.is_recording = False
                stop_recording(self.recording_process) # Kill the ffmpeg process
                
                if len(self.frame_buffer) > 100:
                    self.buffer_file = f"videos/{timeStamp}_buffer.mp4"
                    output_file = f"videos/{timeStamp}_final.mp4"
                    self.concat_thread = save_buffer_and_concatenate_videos(self.frame_buffer, self.buffer_file, self.video_file, output_file)

        # Release the video stream
        cap.release()
        self.running = False

def main(d):
    c = Cam()

    print("Starting cam")
    c.start()
    time.sleep(2)         # should be implemented with queue/signals but good enough for testing
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
    main({"stop": False})
