import serial
import time
from serial.tools import list_ports
import db


'''
Defines a lower level class to handle communication between the Raspberry Pi and the control electronics which handle the front IO
and communication bridge with the servos.

'''

PAN_GEAR_RATIO = 40

def get_op_codes():
        '''
        Returns a dictionary with different possible operations to ESP32 and respective code ex: 'Firmware':0x20
        '''
        return {
            "Firmware":0x20,
            "Dynamixel Write":0x50,
            "Dynamixel Read":0x51,
            "Group Dynamixel Write":0x56,
            "Group Dynamixel Read":0x57,
            "Bulk Dynamixel Read":0x58,
            "Bulk Temperature Read":0x59,
            "Set Shutdown":0x60,
            "Get Shutdown&PushButton":0x61,
            "Set BackPanel LEDs":0x62
        }


class FrontBoardDriver:
    def __init__(self):
        self.command_codes = get_op_codes()
        connected = False
        while not connected:
            ports = serial.tools.list_ports.comports()
            print("Searching for GPIO Front Board ")
            for port in ports:
                if "SurfFrontBoard" in port.description:
                    try:
                        self.serial = serial.Serial(port.device, baudrate=1000000, timeout=2.0)
                        connected = True
                        print("ESP CONNECTED")
                    except Exception as e:
                        print("Connection error: {e}")
            time.sleep(0.1)
        
        self.setBackPanelLEDs(False, False)
        
        self.current_pan_mode = ""
        
        self.setTiltPID(4000, 0, 2000)
        self.dynamixelWrite(1, 108, 3) # Set Tilt profile acceleration 
        self.dynamixelWrite(1, 112, self.toDynamixelVelocity(5))   # Set Tilt profile velocity
        #self.setTiltPID(5000, 1, 10)

        self.PanCenterPulse = self.dynamixelRead(2, 132)  
        
        
        conn = db.get_connection()
        self.commands = db.Commands(conn)
        
        self.panIntendedPlayTime = 0.2 # How much time we want each pan movement to take
        self.lastPanAngle = 0
        
    def send_message(self, msg):
        """
            Writes a pre-built Message to the serial port and checks for successful transmission
            Returns: [True]
            Receives: [0xff ,0xff ,op_code ,data_lenght ,data ,high_value ,low_value]
        """      
        sent_msg = self.serial.write(msg)

        if (sent_msg != len(msg)):
            err_msg = "Error writing message to buffer (sent {} bytes of {})".format(sent_msg, len(msg))
            raise Exception("send_message()", err_msg)   
        
        return True
    
    def parsing_message(self):
        """
            Reads serial port data and parses the returned message
            Returns: [0xff ,0xff ,op_code ,data_lenght ,data ,high_value ,low_value]
            Receives: 
        """
        header = self.serial.read(2)                              # HEADERS (0xff, 0xff)
        
        if len(header) < 2 or header[:2] != b'\xff\xff' :         # Check if header corresponds to expected
            err_msg = "Error with headers {}".format(header)
            raise Exception("parsing_message()", err_msg)
        
        op_code = self.serial.read(1)                             #OP_CODE  

        data_len = self.serial.read(2)                            #DATA_LENGTH      
        if data_len[1] > 255:
            err_msg = "Data Length exceeded (received {})".format(data_len)
            raise Exception("parsing_message()", err_msg)
                
        if data_len[1] > 0:
            data = self.serial.read(data_len[1])                  #DATA    

        high_value = self.serial.read(1)                          #MSB
        low_value = self.serial.read(1)                           #LSB   

        if data_len[1] > 0:
            read_message = header + op_code + data_len + data + high_value + low_value

        else:
            read_message = header + op_code + data_len + high_value + low_value

        return read_message
 
    def read_message(self, msg):
        """
            Verifies if the parsed message is valid and returns just the data portion 
            Returns: [data]
            Receives: [read_message] 
        """
        cmd_buffer = self.parsing_message()

        checksum = int.from_bytes((cmd_buffer[-2:]))
        bytesum = sum(cmd_buffer[2:-2])
        #print("checksum-->", checksum)
        #print("bytesum-->", bytesum)
        
        if sum(cmd_buffer[:2]) == sum(msg[:2]) and bytesum == checksum:
            return cmd_buffer[4:-2]    # [data]
        else: 
            err_msg = "Error with response validity {}".format(cmd_buffer)
            raise Exception("read_message()", err_msg)
        
    def build_message(self, op_code, data=[ ]):
        """
            Build a Message Respecting Communication Protocol with the Board
            Sending Message Structure: [0xff ,0xff ,op_code ,data_lenght ,data ,high_chksum ,low_chksum]
            Receiving Message Structure: [op_code][data]
        """
        msg = [0xff, 0xff]
        
        if op_code not in self.command_codes.values():
            err_msg = "Incorrect op_code (received {})".format(op_code)
            raise Exception("build_message()", err_msg)
        
        if len(data) > 255:
            err_msg = "Data Length exceeded (received {})".format(len(data))
            raise Exception("build_message()", err_msg)

        msg.append(op_code)
        msg.append(0) # high byte is always 0
        msg.append(len(data))
        

        for d in data:
            msg.append(d)

        chk = sum(msg[2:])
        chk_low = chk & 0xff
        chk_high = (chk >> 8) & 0xff
        msg.append(chk_high)
        msg.append(chk_low)
        return msg   
        
    def bsr_message(self, op_code, data):
        """
            Build, Send and Read Message
            Send: [data]
            Receives: [op_code] [data]
        """
        try:
            msg = self.build_message(op_code, data)
            self.send_message(msg)
            time.sleep(0.01)
            read_msg = self.read_message(msg)
            return read_msg
        except Exception as e:
            print(f"Error in comm with front board {e} ")
        
    def getFirmware(self):
        return self.bsr_message(0x20, [])
    
    def setBackPanelLEDs(self, first = False, second = False):
        if not first and not second:
            self.bsr_message(self.command_codes["Set BackPanel LEDs"], [0x00])
        elif first and not second:
            self.bsr_message(self.command_codes["Set BackPanel LEDs"], [0x01])
        elif not first and second:
            self.bsr_message(self.command_codes["Set BackPanel LEDs"], [0x02])    
        else:
            self.bsr_message(self.command_codes["Set BackPanel LEDs"], [0x03])
        
    def getShutdownState(self):
        response = self.bsr_message(self.command_codes["Get Shutdown&PushButton"], [])
        msg = int.from_bytes(response, byteorder='big')
        # Extracting the last 2 bits
        last_2_bits = msg & 0b11

        # Extracting individual bits
        ButtonPressed = (msg >> 1) & 1  # Extracting the second last bit
        ShutdownSequence = msg & 1          # Extracting the last bit
        #print(f"Is the button pressed: {ButtonPressed} and Is Shutting Down?: {ShutdownSequence}")
        return ShutdownSequence
    
    def setShutdown(self, seconds=15):
        bytes_val = seconds.to_bytes(2, 'little') 
        self.bsr_message(self.command_codes["Set Shutdown"], [bytes_val])
        time.sleep(1)
        
    def bulkReadTemp(self):
        response = self.bsr_message(self.command_codes["Bulk Temperature Read"], [0x00])
        nReadings = response[0]
        IDTILT = response[1]
        ERRORTILT = response[2]
        TEMPTILT = response[3]
        IDPAN = response[4]
        ERRORPAN = response[5]
        TEMPPAN = response[6]
        print(f"Motor {IDTILT} has {ERRORTILT} errors and Temp {TEMPTILT} C")
        print(f"Motor {IDPAN} has {ERRORPAN} errors and Temp {TEMPPAN} C")
        return TEMPTILT, TEMPPAN
        
    def bulkReadPosVel(self):
        response = self.bsr_message(self.command_codes["Bulk Dynamixel Read"], [0x00])
        nLen = response[0]
        IDTILT = response[1]
        ERRORTILT = response[2]
        
        tiltpos_h = response[3]
        tiltpos_l = response[4]
        bytelist = [tiltpos_h, tiltpos_l]
        tiltpos_int = int.from_bytes(bytearray(bytelist), "big")
        
        tiltvel_h = response[5]
        tiltvel_l = response[6]
        bytelist = [tiltvel_h, tiltvel_l]
        tiltvel_int = int.from_bytes(bytearray(bytelist), "big")
        
        IDPAN = response[7]
        ERRORPAN = response[8]
        
        panpos_h = response[9]
        panpos_l = response[10]
        bytelist = [panpos_h, panpos_l]
        panpos_int = int.from_bytes(bytearray(bytelist), "big")
        
        panvel_h = response[11]
        panvel_l = response[12]
        bytelist = [panvel_h, panvel_l]
        panvel_int = int.from_bytes(bytearray(bytelist), "big")
        
        return tiltpos_int, tiltvel_int, panpos_int, panvel_int        
        
    def dynamixelRead(self, ID,  ADDR):
        ADDR_bytes = ADDR.to_bytes(2, byteorder="little")
        ADDR_H = ADDR_bytes[1]
        ADDR_L = ADDR_bytes[0]
        data2send = bytearray([ID, ADDR_H, ADDR_L])
        response = self.bsr_message(self.command_codes["Dynamixel Read"], data2send)
        
        data_bytes = response[-4:]
        result = int.from_bytes(data_bytes, byteorder='big', signed=True)
        return result
        
    def dynamixelWrite(self, ID, ADDR, data):
        ADDR_bytes = ADDR.to_bytes(2, byteorder="little")
        ADDR_H = ADDR_bytes[1]
        ADDR_L = ADDR_bytes[0]
        
        data_bytes = data.to_bytes(4, byteorder='little', signed=True)
        # Extract Data bytes
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        
        data2send = bytearray([ID, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        response = self.bsr_message(self.command_codes["Dynamixel Write"], data2send)
        
    def turnOnTorque(self):
        ID1 = 0x01
        ID2 = 0x02
        
        ADDR = 64
        data = 1
        
        ADDR_bytes = ADDR.to_bytes(2, byteorder="little")
        ADDR_H = ADDR_bytes[1]
        ADDR_L = ADDR_bytes[0]
        
        data_bytes = data.to_bytes(4, byteorder='little')
        # Extract Data bytes
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        
        NCOMMANDS = 2
        
        data2send = bytearray([NCOMMANDS, ID1, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0, ID2, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        #print("Torque Turned ON on both Axis")
        
        self.setTiltPID(4000, 0, 2000)
        
        self.dynamixelWrite(1, 108, 10) # Set Tilt profile acceleration 
        self.dynamixelWrite(1, 112, self.toDynamixelVelocity(10))   # Set Tilt profile velocity
        
    def turnOffTorque(self):
        ID1 = 0x01
        ID2 = 0x02
        
        ADDR = 64
        data = 0
        
        ADDR_bytes = ADDR.to_bytes(2, byteorder="little")
        ADDR_H = ADDR_bytes[1]
        ADDR_L = ADDR_bytes[0]
        
        data_bytes = data.to_bytes(4, byteorder='little')
        # Extract Data bytes
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        
        data2send = bytearray([2, ID1, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0, ID2, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        #print("Torque Turned OFF on both Axis")
        
    def getPanPID(self):
        ADDR = [80, 82, 84]
        NCOMMANDS = 3
        ID = 2
        msg = [NCOMMANDS]
        
        for addr in ADDR:
            ADDR_bytes = addr.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_bytes[1]
            ADDR_L = ADDR_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L])
            
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Read"], data2send)
        
        D = int.from_bytes(response[1:5], byteorder='big')
        I = int.from_bytes(response[5:9], byteorder='big')
        P = int.from_bytes(response[9:13], byteorder='big')
        
        print("     Pan PID Parameters")
        print(f"    P: {P}   I: {I}   D: {D}")
        
        return P, I, D
    
    def getPanVelocityPI(self):
        ADDR = [76, 78]
        NCOMMANDS = 2
        ID = 2
        msg = [NCOMMANDS]
        
        for addr in ADDR:
            ADDR_bytes = addr.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_bytes[1]
            ADDR_L = ADDR_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L])
            
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Read"], data2send)
        
        I = int.from_bytes(response[1:5], byteorder='big')
        P = int.from_bytes(response[5:9], byteorder='big')
        
        print("     Pan Velocity PI Parameters")
        print(f"    P: {P}   I: {I}   ")
        
        return P, I
    
    def getTiltPID(self):
        ADDR = [80, 82, 84]
        NCOMMANDS = 3
        ID = 1
        msg = [NCOMMANDS]
        
        for addr in ADDR:
            ADDR_bytes = addr.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_bytes[1]
            ADDR_L = ADDR_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L])
            
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Read"], data2send)
        
        D = int.from_bytes(response[1:5], byteorder='big')
        I = int.from_bytes(response[5:9], byteorder='big')
        P = int.from_bytes(response[9:13], byteorder='big')
        
        print("     Tilt PID Parameters")
        print(f"    P: {P}   I: {I}   D: {D}")
        
        return P, I, D
            
    def setPanPID(self, P, I, D):
        ID = 2
        NCOMMANDS = 3
        msg = [NCOMMANDS]
        
        ADDR = [84, 82, 80]
        
        P_ADDR_BYTES = ADDR[0].to_bytes(2, byteorder="little")
        P_ADDR_H = P_ADDR_BYTES[1]
        P_ADDR_L = P_ADDR_BYTES[0]
        data_bytes = P.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, P_ADDR_H, P_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        I_ADDR_BYTES = ADDR[1].to_bytes(2, byteorder="little")
        I_ADDR_H = I_ADDR_BYTES[1]
        I_ADDR_L = I_ADDR_BYTES[0]
        data_bytes = I.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, I_ADDR_H, I_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        D_ADDR_BYTES = ADDR[2].to_bytes(2, byteorder="little")
        D_ADDR_H = D_ADDR_BYTES[1]
        D_ADDR_L = D_ADDR_BYTES[0]
        data_bytes = D.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, D_ADDR_H, D_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        #print("Pan PID Parameters Updated")
        
    def setPanVelocityPI(self, P, I):
        ID = 2
        NCOMMANDS = 2
        msg = [NCOMMANDS]
        
        ADDR = [78, 76]
        
        P_ADDR_BYTES = ADDR[0].to_bytes(2, byteorder="little")
        P_ADDR_H = P_ADDR_BYTES[1]
        P_ADDR_L = P_ADDR_BYTES[0]
        data_bytes = P.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, P_ADDR_H, P_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        I_ADDR_BYTES = ADDR[1].to_bytes(2, byteorder="little")
        I_ADDR_H = I_ADDR_BYTES[1]
        I_ADDR_L = I_ADDR_BYTES[0]
        data_bytes = I.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, I_ADDR_H, I_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        #print("Pan PID Parameters Updated")

    def setTiltPID(self, P, I, D):
        ID = 1
        NCOMMANDS = 3
        msg = [NCOMMANDS]
        
        ADDR = [84, 82, 80]
        
        P_ADDR_BYTES = ADDR[0].to_bytes(2, byteorder="little")
        P_ADDR_H = P_ADDR_BYTES[1]
        P_ADDR_L = P_ADDR_BYTES[0]
        data_bytes = P.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, P_ADDR_H, P_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        I_ADDR_BYTES = ADDR[1].to_bytes(2, byteorder="little")
        I_ADDR_H = I_ADDR_BYTES[1]
        I_ADDR_L = I_ADDR_BYTES[0]
        data_bytes = I.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, I_ADDR_H, I_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        D_ADDR_BYTES = ADDR[2].to_bytes(2, byteorder="little")
        D_ADDR_H = D_ADDR_BYTES[1]
        D_ADDR_L = D_ADDR_BYTES[0]
        data_bytes = D.to_bytes(4, byteorder="little")
        data_31_24 = data_bytes[3]
        data_23_16 = data_bytes[2]
        data_15_8 = data_bytes[1]
        data_7_0 = data_bytes[0]
        msg.extend([ID, D_ADDR_H, D_ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
        
        data2send = bytearray(msg)
        response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        #print("Tilt PID Parameters Updated")
        
    def int_to_signed_bytes(self, value, length):
        # Check if the integer is negative
        if value < 0:
            # Calculate the two's complement of the negative number
            value = (1 << (length * 8)) + value
        return value.to_bytes(length, byteorder='little')

    def groupDynamixelSetPosition(self, tiltpos=None, tiltvel=None, panpos=None, panvel=None):
        NCOMMANDS = 0
        msg = []
        if tiltpos:
            ID = 1
            ADDR = 116
            ADDR_BYTES = ADDR.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_BYTES[1]
            ADDR_L = ADDR_BYTES[0]
            data_bytes = tiltpos.to_bytes(4, byteorder="little")
            data_31_24 = data_bytes[3]
            data_23_16 = data_bytes[2]
            data_15_8 = data_bytes[1]
            data_7_0 = data_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
            NCOMMANDS += 1
        if tiltvel:
            ID = 1
            ADDR = 112
            ADDR_BYTES = ADDR.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_BYTES[1]
            ADDR_L = ADDR_BYTES[0]
            data_bytes = tiltvel.to_bytes(4, byteorder="little")
            data_31_24 = data_bytes[3]
            data_23_16 = data_bytes[2]
            data_15_8 = data_bytes[1]
            data_7_0 = data_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
            NCOMMANDS += 1
        if panpos:
            ID = 2
            ADDR = 116
            ADDR_BYTES = ADDR.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_BYTES[1]
            ADDR_L = ADDR_BYTES[0]
            data_bytes = panpos.to_bytes(4, byteorder="little", signed=True)
            data_31_24 = data_bytes[3]
            data_23_16 = data_bytes[2]
            data_15_8 = data_bytes[1]
            data_7_0 = data_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
            NCOMMANDS += 1
        if panvel:
            ID = 2
            ADDR = 112
            ADDR_BYTES = ADDR.to_bytes(2, byteorder="little")
            ADDR_H = ADDR_BYTES[1]
            ADDR_L = ADDR_BYTES[0]
            data_bytes = panvel.to_bytes(4, byteorder="little")
            data_31_24 = data_bytes[3]
            data_23_16 = data_bytes[2]
            data_15_8 = data_bytes[1]
            data_7_0 = data_bytes[0]
            msg.extend([ID, ADDR_H, ADDR_L, data_31_24, data_23_16, data_15_8, data_7_0])
            NCOMMANDS += 1
            
        if NCOMMANDS > 0:
            msg.insert(0, NCOMMANDS)
            data2send = bytearray(msg)
            response = self.bsr_message(self.command_codes["Group Dynamixel Write"], data2send)
        else:
            return

        
    def setAngles(self, pan, tilt=None, pan_speed=None, tilt_speed=None):        

        pan = min(max(-90, pan), 90)
        tilt = min(max(0, tilt), 45)
                
        pan_input_min = -90
        pan_input_max = 90
        #pan_output_min = -2045   
        #pan_output_max = 2045
        # In Extended Position Mode, range is actually -1048575 to 1048575 eq to -256to256 rev. So for -90 to 90 it should be -1024 to 1024
        pan_output_min = -1024
        pan_output_max = 1024

        tilt_input_min = 0
        tilt_input_max = 45
        tilt_output_min = 1990
        tilt_output_max = 2500

        pan_dynamixel_value = self.PanCenterPulse + round(PAN_GEAR_RATIO * int((pan - pan_input_min) * (pan_output_max - pan_output_min) / (pan_input_max - pan_input_min) + pan_output_min))
        tilt_dynamixel_value = int((tilt - tilt_input_min) * (tilt_output_max - tilt_output_min) / (tilt_input_max - tilt_input_min) + tilt_output_min)
                
        if pan_speed: # If pan_speed value is provided, use the given value
            pan_speed = pan_speed
        else: # #If not pan_speed value is provided, calculate the speed to achieve the desired playtime
            anglediff = pan - self.getCurrentPanAngle()
            pan_speed = anglediff / self.panIntendedPlayTime
            pan_speed = min(abs(pan_speed), 6)#self.commands.max_pan_speed)

        self.dynamixelWrite(2, 112, self.toDynamixelVelocity(pan_speed * 40))   # Set profile velocity
        
        self.groupDynamixelSetPosition(panpos = pan_dynamixel_value, tiltpos = tilt_dynamixel_value)
        return True
    
    def setTiltAngle(self, tilt):
        self.dynamixelWrite(2, 64, 1)   # Turn ON the torque on the pan motor
        
        tilt  = min(max(0,tilt),45)
                
        tilt_input_min = 0
        tilt_input_max = 45
        tilt_output_min = 1990
        tilt_output_max = 2500
        
        tilt_dynamixel_value = int((tilt - tilt_input_min) * (tilt_output_max - tilt_output_min) / (tilt_input_max - tilt_input_min) + tilt_output_min)

        id = 1
        adr = 116
        self.dynamixelWrite(id, adr, tilt_dynamixel_value)        
        
    def testPan(self):
        import random
        self.setAngles(pan = 0, tilt = 0)
        time.sleep(1)
        for panAngle in range(0, 90):
            self.setAngles(pan = panAngle , tilt = 0)
            time.sleep(.2)
        for panAngle in range(0, 90):
            self.setAngles(pan = 90 - panAngle , tilt = 0)
            time.sleep(.2)
            
    def testTilt(self):
        self.setAngles(pan = 0, tilt = 0)
        time.sleep(1)
        for tiltAngle in range(-5, 40):
            self.setAngles(pan = 0, tilt = tiltAngle)
            print(tiltAngle)
            time.sleep(0.1)
        for tiltAngle in reversed(range(-5, 40)):
            print(tiltAngle)
            self.setAngles(pan=0, tilt=tiltAngle)
            time.sleep(0.1)
            
    def toDynamixelVelocity(self, degrees_per_second):
        ''' Takes a velocity in º/s and converts it to the dynamixel units (integer multiples of 0.229 rpm) '''
        to_rpm = degrees_per_second / 6 
        unit = 0.229 # Dynamixel base unit in RPM. The servos work in integer multiples of this value
        dynamixel_val = to_rpm / unit
        dynamixel_val = max(min(abs(dynamixel_val), 2047), 0) # value range is 0 to 2047, but value will be limited by the velocity limit
        if degrees_per_second < 0:
            return -round(dynamixel_val) 
        return round(dynamixel_val)
    
    def setPanVelocityControl(self, velocityLimit = 250):  
        if self.current_pan_mode != "velocity":
            self.current_pan_mode = "velocity"
            self.dynamixelWrite(2, 64, 0)   # Turn OFF pan torque
            self.setPanGoalVelocity(0)
            self.dynamixelWrite(2, 11, 1)   # Set operating Mode (11) to Velocity Mode (1)
            dyna_val = self.toDynamixelVelocity(velocityLimit) # Max speed of the motor: 250/40 ~ 6º/s pan speed
            self.dynamixelWrite(2, 44, dyna_val)    # Set Velocity Limit (44)
            #self.setPanVelocityPI(1500, 1500)   # Over 10 deg/s
            self.setPanVelocityPI(160, 1600)
            self.dynamixelWrite(2, 108, 50)  # Set profile acceleration 
            self.dynamixelWrite(2, 64, 1)   # Turn ON the torque on the pan motor
        
    def setPanPositionControl(self):
        if self.current_pan_mode != "position":
            self.current_pan_mode = "position"
            self.dynamixelWrite(2, 64, 0)   # Turn OFF pan torque
            self.setPanGoalVelocity(0)
            self.dynamixelWrite(2, 11, 4)  # Set operating mode to Extended position
            self.setPanPID(1500, 0, 150) 
            self.dynamixelWrite(2, 108, 15) # Set profile acceleration 
            self.setProfileVelocity(120)
            #self.dynamixelWrite(2, 112, self.toDynamixelVelocity(25))  # Set profile velocity: 0.229/40 * val  deg/s
            self.turnOnTorque()
            
    def setProfileVelocity(self, velocity):
        dval = self.toDynamixelVelocity(velocity * 40)
        self.dynamixelWrite(2, 112, dval)
        
    def setPanGoalVelocity(self, degreespersecond):
        ''' Sets the camera pan rotation speed in º/s when in velocity control mode'''
        dyna_val = self.toDynamixelVelocity(degreespersecond * PAN_GEAR_RATIO)
        self.dynamixelWrite(2, 104, dyna_val)    # Set Goal Velocity (104)
        
    def getCurrentPanAngle(self):
        currentpulse = self.dynamixelRead(2, 132) 
        dif = currentpulse - self.PanCenterPulse
        angle = dif * 90 / 1024 / 40
        return round(angle, 2)
