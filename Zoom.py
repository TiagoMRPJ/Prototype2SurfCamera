import numpy as np
#import cv2
import serial.tools.list_ports
import time
import math


class SoarCameraZoomFocus:
    def __init__(self):

        connected = False
        while not connected:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "IDMind SurfCamera2 ZoomFocus" in port.description:
                    try:
                        self.serial = serial.Serial(
                            port.device,
                            baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            stopbits=serial.STOPBITS_ONE,
                            parity=serial.PARITY_NONE,
                            timeout=5.0
                        )
                        connected = True
                        print("Connected to Camera Zoom/Focus Motors")
                        break
                    except Exception as e:
                        print("Connection error: {e}")
            time.sleep(0.1)   
        
        # Set the zoom speed to the minimum on both directions
        self.set_zoom_speed(0, "tele")
        time.sleep(1)
        self.set_zoom_speed(0, "wide")
        time.sleep(1)
    
        
    def testSerialReception(self):
        try:
            while True:
                if self.serial.in_waiting > 0:
                    response = self.serial.read(self.serial.in_waiting)  # Read available bytes
                    print(f"Received: {response.hex()}")  # Print the response as a hex string
                time.sleep(0.1)  # Avoid busy waiting
        except KeyboardInterrupt:
            print("Stopping listener")
        except Exception as e:
            print(f"Error while receiving data: {e}")
    
    def testSerialSending(self, msg):
        while True:
            self.sendMsg(msg)
            time.sleep(1)
        
    def sendMsg(self, msg):
        if isinstance(msg, str):
            bytes2send = bytes(msg, "utf-8")
        else:
            bytes2send = msg
        self.serial.write(bytes2send)
    
    def receiveResponse(self):
        try:
            response = self.serial.read(1024)  # Read up to 1024 bytes
            if response:
                return response.hex()  # Convert bytes to hex string
            else:
                print("No response received")
                return None
        except serial.SerialTimeoutException:
            print("No response received within the timeout period")
            return None
        
    def zoomToCoordinate(self, zoomLevel):
        '''zoomLevel should be between 1-30'''
        zoomLevel = max(min(zoomLevel, 30), 0)
        maxZoom = 30
        maxVal = 0x4000
        zoomPos = int((zoomLevel / maxZoom) * maxVal)
        p = (zoomPos >> 12) & 0xF
        q = (zoomPos >> 8) & 0xF
        r = (zoomPos >> 4) & 0xF
        s = zoomPos & 0xF
        msg = f"8x010447{p:X}{q:X}{r:X}{s:X}FF"
        #msg = "8x010447 0p0q0r0sFF"
        self.sendMsg(msg)
    
    def setMinZoom(self):
        msg = [0x81, 0x01, 0x04, 0x07, 0x03, 0xFF]    
        self.sendMsg(msg)
    
    def setMaxZoom(self):
        zoom_in_command = [0x81, 0x01, 0x04, 0x07, 0x02, 0xFF]
        self.sendMsg(zoom_in_command)
        
    def set_zoom_position(self, zoomValue):
        '''
        Sets the camera's zoom to a value between 1x and 30x
        '''
        
        zoomValue = max(min(zoomValue,30), 0)
        
        zoom_positions = [0, 5370, 8080, 9890, 11190, 
                               12150, 12880, 13560, 14125, 14550, 
                               14915, 15200, 15450, 15640, 15800, 
                               15932, 16030, 16112, 16135, 16160, 
                               16183, 16205, 16228, 16253, 16275, 
                               16296, 16318, 16340, 16362, 16385]
        
        if isinstance(zoomValue, int):
            zoom_position = zoom_positions[zoomValue -1]
        else:
            # If it's not an integer, ex. 5.3x
            # Interpolate 
            x0, y0 = math.floor(zoomValue), zoom_positions[math.floor(zoomValue) - 1]
            x1, y1 = math.floor(zoomValue) + 1, zoom_positions[math.floor(zoomValue)]
            zoom_position = y0 + (zoomValue - x0) * (y1-y0) / (x1-x0)
            zoom_position = int(zoom_position)
        
        # Split the zoom position into four nibbles (each 4 bits)
        p = (zoom_position >> 12) & 0xF
        q = (zoom_position >> 8) & 0xF
        r = (zoom_position >> 4) & 0xF
        s = zoom_position & 0xF
        
        # Construct the command
        zoom_command = [0x81, 0x01, 0x04, 0x47, p, q, r, s, 0xFF]
        self.sendMsg(zoom_command)
        
    def set_zoom_speed(self, zoomSpeedValue, direction="tele"):
        '''
        Sets the zoom speed. 
        zoomSpeedValue should be an integer between 0 and 7.
        direction can be either "tele" for zooming in or "wide" for zooming out.
        '''
        # Ensure the speed value is within the valid range (0 to 7)
        zoomSpeedValue = max(min(zoomSpeedValue, 7), 0)
        
        # Determine the command based on the direction
        if direction == "tele":
            zoom_command = [0x81, 0x01, 0x04, 0x07, 0x20 | zoomSpeedValue, 0xFF]
        elif direction == "wide":
            zoom_command = [0x81, 0x01, 0x04, 0x07, 0x30 | zoomSpeedValue, 0xFF]
        else:
            raise ValueError("Direction must be 'tele' (zoom in) or 'wide' (zoom out)")
        
        # Send the zoom speed command
        self.sendMsg(zoom_command)
