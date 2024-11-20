import requests
#import db
import time
from collections import Counter

class PublicIPHandler:
    """
    Implements a class for checking the current public IP address of the router and updating it accordingly if needed.
    This is needed when the ISP provider does not guarantee a static IP address for the router and so the connection from the WebApp to Camera's API may be broken.
    ([publicIP]:[port]/[route] to access the API so if publicIP changes without the WebApp knowing, it wont be able utilize the Camera)
    """

    def method1(self):
        import os

        ext_ip = os.popen("curl -s ifconfig.me").readline()
        return ext_ip

    def method2(self):
        from requests import get

        ext_ip = get("https://api.ipify.org", timeout=5).content.decode("utf8")
        return ext_ip

    def method3(self):
        import urllib.request

        ext_ip = urllib.request.urlopen("https://ident.me").read().decode("utf8")
        return ext_ip

    def method4(self):
        import requests

        ext_ip = requests.get("https://checkip.amazonaws.com", timeout=5).text.strip()
        return ext_ip

    """ def method5(self):
        import pynat

        topology, ext_ip, ext_port = pynat.get_ip_info()
        return ext_ip """

    def method6(self):
        from requests import get

        ext_ip = get("http://ipgrab.io", timeout=5).text.strip()
        return ext_ip

    def is_valid_ip(self, ip):
        # Regular expression to match valid IPv4 addresses
        import re

        pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        return pattern.match(ip) is not None

    def checkIP(self):
        methods = [
            self.method1,
            self.method2,
            self.method3,
            self.method4,
            #self.method5,
            self.method6,
        ]
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
        """
        Checks if there is an available internet connection utilizing a google DNS
        """
        import socket

        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except OSError:
            return False

    def get_public_ip(self):
        """
        Starts by checking for an available internet connection. Then checks the current public IP address through different services.
        Returns the current public IP address
        """
        # Wait until we get an internet connection
        print("Checking for an internet connection...")
        while not self.is_connected():
            time.sleep(1)
        print("Connected to the internet!")

        IP = self.checkIP()  # Get the current public IP address from different services
        return IP

publicIP = PublicIPHandler()

# Configuration
BASE_URL = "https://directus-mrzmb2r22q-no.a.run.app/"  # Replace with your Directus instance URL
EMAIL = "maevaplasse@surfrec.com"  # Replace with your Directus email
PASSWORD = "Maeva123!@#"  # Replace with your Directus password

TABLE_NAME = "cameras"    # Replace with your table name

# Authentication
def authenticate():
    url = f"{BASE_URL}/auth/login"
    payload = {"email": EMAIL, "password": PASSWORD}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Fetch data from a table
def get_table_data(headers, filters=None):
    url = f"{BASE_URL}/items/{TABLE_NAME}"
    params = {"filter": filters} if filters else {}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Write data into a table
def write_table_data(headers, data):
    url = f"{BASE_URL}/items/{TABLE_NAME}"
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Update data in a table
def update_table_entry(headers, entry_id, data):
    """
    Update an entry in the Directus table.
    
    :param headers: Authentication headers
    :param entry_id: ID of the entry to update
    :param data: Dictionary with the fields to update
    """
    url = f"{BASE_URL}/items/{TABLE_NAME}/{entry_id}"
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 404:
        print(f"Entry with ID {entry_id} not found.")
    response.raise_for_status()  # Raise an error if request fails
    return response.json()

def get_local_ip():
    import socket

    local_hostname = socket.gethostname()
    ip_addresses = socket.gethostbyname(local_hostname)
    # print(ip_addresses)
    """ # Step 3: Filter out loopback addresses (IPs starting with "127.").
    filtered_ips = [ip for ip in ip_addresses if not ip.startswith("127.")]
    # Step 4: Extract the first IP address (if available) from the filtered list.
    print(filtered_ips) """
    return ip_addresses

def find_and_update_API_Address():
    """
    Gets the current external IP and checks against the last known one. If it is the same, returns. If it has changed, the address entry on directus table is changed to the new one.
    """
    previous_address = ""  # Change for DB retrieval of old address
    current_ext_ip = publicIP.get_public_ip()  # Retrieve the current public IP address
    localip = get_local_ip()
    new_address = f"http://{current_ext_ip}:500{localip[-1]}"
    
    if False:
        print(f"previous_address {previous_address}")
        print(f"current_ext_ip {current_ext_ip}")
        print(f"local_ip {localip}")
        print(f"new_address {new_address}")
    
    if not previous_address: # If there still isn't any previous stored address, store it and create an entry on the Cameras Table 
        print("No previous API address in memory. Creating Table Entry in Directus")
        previous_address = new_address
        headers = authenticate() # Log in Directus to retrieve Authentication Tokens
        table_data = get_table_data(headers) # Request the "Cameras" table from Directus
        for entry in table_data["data"]:    
            if entry["address"] == new_address:    # Find the Cameras Table Entry corresponding to the previous Address
                print(f"Directus table entry already found for current address ({new_address})")
                return
        # If there isnt already an entry for the current address, create it
        data = {'address': new_address , 'api_key': 'xxx', 'available': False}
        write_table_data(headers, data)
        return
    
    if previous_address == new_address:  # If there was no change, do nothing
        print("API Address (Directus) is up to date.")
        return
    
    # If ext ip has changed, continue
    print("API Address has changed. Accessing Directus to update...")
    
    # Authenticate into directus and retrieve the Cameras table
    headers = authenticate() # Log in Directus to retrieve Authentication Tokens
    table_data = get_table_data(headers) # Request the "Cameras" table from Directus
    for entry in table_data["data"]:    
        if entry["address"] == previous_address:    # Find the Cameras Table Entry corresponding to the previous Address
            entryID = entry["id"]
            print(f"Updating API Address on Directus")
            update_table_entry(headers, entryID, {"address": new_address})
            previous_address == new_address
            return

# Main
if __name__ == "__main__":
    find_and_update_API_Address()
    # get_local_ip()
