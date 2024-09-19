import subprocess
import os
import time
def start_ffmpeg_buffer(ip_camera_url, fifo_path="/tmp/camera_buffer"):
    """
    Start an FFmpeg process to buffer video in memory using a FIFO (named pipe).

    :param ip_camera_url: The RTSP URL of the IP camera stream.
    :param fifo_path: Path to the FIFO (named pipe) for buffering video.
    :return: The subprocess.Popen object running FFmpeg.
    """
    if os.path.exists(fifo_path):
        os.remove(fifo_path)

    # FFmpeg command to continuously write to FIFO
    ffmpeg_command = [
        "ffmpeg",
        "-rtsp_transport", "tcp",  # Use TCP for RTSP to improve reliability
        "-i", ip_camera_url,        # Input stream from IP camera
        "-vf", "fifo",              # Use FIFO to buffer the stream in memory
        "-t", "5",
        "-f", "mpegts",             # Output format
        fifo_path                   # Output to FIFO pipe
    ]

    # Start the FFmpeg process
    subprocess.run(ffmpeg_command)
   # process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
   # return process

def start_recording(output_file, fifo_path="/tmp/camera_buffer", ip_camera_url=None):
    """
    Start recording video from the FIFO buffer and continue with the live stream.

    :param output_file: Path where the recorded video will be saved.
    :param fifo_path: Path to the FIFO (named pipe) used for buffering.
    :param ip_camera_url: The RTSP URL of the IP camera stream (for live continuation).
    :return: The subprocess.Popen object running the recording.
    """
    ffmpeg_command = [
        "ffmpeg",
        "-i", fifo_path,                           # Input from FIFO buffer
        "-i", ip_camera_url,                       # Input from the live stream
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0 [v]",  # Concatenate buffered and live streams
        "-map", "[v]",                             # Use the concatenated video stream
        output_file                                # Output file
    ]

    # Start the FFmpeg recording process
    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return process

def stop_recording(process):
    """
    Stop the recording process gracefully.

    :param process: The subprocess.Popen object representing the FFmpeg process.
    """
    process.stdin.write('q'.encode('GBK'))
    process.communicate()
    #process.terminate()  # Gracefully terminate the process
    #process.wait()       # Wait for the process to fully exit

# Example usage:
ip_camera_url = 'rtsp://admin:IDMind2000!@192.168.1.68'

# Start buffering in a FIFO
buffer_process = start_ffmpeg_buffer(ip_camera_url, fifo_path="videos/camera_buffer")

# Simulate a delay or detection of movement
time.sleep(3)  # Simulate waiting for movement detection

buffer_process.terminate()
buffer_process.wait()

# Record video from the buffer and continue with the live stream
""" output_file = "output_with_prebuffer.mp4"
p = start_recording(output_file, fifo_path="videos/camera_buffer", ip_camera_url=ip_camera_url)
time.sleep(2)
stop_recording(p)


# Terminate the buffer process
buffer_process.terminate()
buffer_process.wait() """
