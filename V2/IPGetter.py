from collections import Counter
import time
import sys
sys.path.append('/home/IDMind/Documents/V1/')
import db


'''
Implements a class for checking the current public IP address of the router and updating it accordingly if needed.
This is needed when the ISP provider does not guarantee a static IP address for the router and so the connection from the WebApp to Camera's API may be broken.
([publicIP]:[port]/[route] to access the API so if publicIP changes without the WebApp knowing, it wont be able utilize the Camera)
'''

class PublicIPHandler():
    def __init__(self):
        conn = db.get_connection()
        self.webapp = db.WebApp(conn)
        
    def method1(self):
        import os
        ext_ip  = os.popen('curl -s ifconfig.me').readline()
        return ext_ip
    
    def method2(self):
        from requests import get
        ext_ip = get('https://api.ipify.org', timeout=5).content.decode('utf8')
        return ext_ip
    
    def method3(self):
        import urllib.request
        ext_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')  
        return ext_ip
    
    def method4(self):
        import requests
        ext_ip = requests.get('https://checkip.amazonaws.com', timeout =5).text.strip()
        return ext_ip
    
    def method5(self):
        import pynat
        topology, ext_ip, ext_port = pynat.get_ip_info()
        return ext_ip
    
    def method6(self):
        from requests import get
        ext_ip = get('http://ipgrab.io', timeout =5).text.strip()
        return ext_ip
    
    def is_valid_ip(self, ip):
        # Regular expression to match valid IPv4 addresses
        import re
        pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        return pattern.match(ip) is not None
    
    def checkIP(self):
        methods = [self.method1, self.method2, self.method3, self.method4, self.method5, self.method6]
        valid_ips = []

        for method in methods:
            try:
                ip = method()
                if self.is_valid_ip(ip):
                    valid_ips.append(ip)
            except Exception as e:
                # Catch any exceptions and skip to the next method
                print(f"Error in {method.__name__}: {e}")
        
        if valid_ips:
            # Count the occurrences of each valid IP
            ip_counts = Counter(valid_ips)
            # Get the IP that appears the most
            most_common_ip, count = ip_counts.most_common(1)[0]
            # If it is returned by most methods, return it
            if count >= len(methods) // 2:
                return most_common_ip
            else:
                print("No consensus on IP address.")
        else:
            print("No valid IPs found.")
            
    def is_connected(self, host="8.8.8.8", port=53, timeout=3):
        '''
        Checks if there is an available internet connection utilizing a google DNS
        '''
        import socket
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except OSError:
            return False
        
    def check_and_update_ip(self):
        '''
        Runs at every system boot.
        Starts by checking for an available internet connection. Then checks the current public IP address through different methods and compares it to the last known.
        If it has changed, updates the internal memory and sends this new public IP along with the camera identification to the WebApp server.
        '''
        # Wait until we get an internet connection
        print("Checking for an internet connection...")
        while not self.is_connected():
            time.sleep(1)
        print("Connected to the internet!")
        
        IP = self.checkIP() # Get the current public IP address from different services
        if IP != self.webapp.PublicIP: # if the new public IP is not the same as the previous public IP
            self.webapp.PublicIP = IP # Update it internally
            self.webapp.client.dump(["PublicIP"], "db.txt")
            self.send_new_public_ip_to_server() # Send the updated public IP to the WebApp server
        else:
            print(f"Public IP Address is still the same as before {self.webapp.PublicIP}")
            
    def send_new_public_ip_to_server(self):
        '''
        Sends the newly discovered public IP address to the WebApp server for maintaining connectivity
        '''
        import requests
        print(f"Hello WebApp Server, I am Camera Unit {self.webapp.CameraID} and my public IP address has changed to {self.webapp.PublicIP}")  
        # Implement sending the new Public IP to the server side   
            
ipa = PublicIPHandler()
ipa.check_and_update_ip()