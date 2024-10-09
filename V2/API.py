import json
import sys
import os
sys.path.append('/home/IDMind/Documents/V1/')
import db # type: ignore
import time


from SessionHandler import create_session_directories
from flask import Flask, jsonify, request, make_response

'''
Implements a Flask server to serve as a system API to be utilized by the WebApp.
Includes methods for starting and stopping the session. 
'''

def validID(id):
    try:
        if int(id) == -1:
            return False
        return True
    except:
        return False

def verifyAuthentication(r):
    try:
        headers = r.headers
        auth = headers.get("X-Api-Key") 
        if auth != webapp.CameraSecurityToken:
            return False
    except:
        return False
    
    return True

conn = db.get_connection()
gps_points = db.GPSData(conn)
commands = db.Commands(conn)
camera_state = db.CameraState(conn)
webapp = db.WebApp(conn)

app = Flask(__name__)

@app.route('/start_session', methods=['POST'])
def start_session():
    """
    Route to start a new session.
    Receives:
    {'SessionID': , 'SessionType':}
    Returns: JSON containing a boolean to indicate success or not and in case of error an error message ("Invalid SessionID", "Session Already Established") 
    {'success': , 'message': } 
    """
    
    if not request.is_json:
        print("Bad JSON on request")
        return jsonify({"success": False, "message": "Invalid or missing JSON data"}), 400

    if not verifyAuthentication(request):
        return jsonify({"success": False, "message": "Wrong or None Authorization Header"}), 401

    # Retrieve the SessionID and Type
    SESSIONID = request.json.get('SessionID', -1)
    SESSIONTYPE = request.json.get('SessionType', 'Single')
    
    if webapp.SessionID != -1:
        print("Session Already Established")
        return jsonify({ "success": False, "message": "Session Already Established" }), 200
    if not validID(SESSIONID):
        print("Invalid SessionID Received")
        return jsonify({ "success": False, "message": "Invalid SessionID" }), 200
    
    webapp.SessionID = SESSIONID
    webapp.SessionStartTime = time.time()
    commands.tracking_enabled = True
    camera_state.enable_auto_recording = True
    create_session_directories(webapp.SessionID)   # Create, if still doesnt exist, the local dirs for storing the sessions videos and gps logs
    print(f"Starting Session {SESSIONID} on {SESSIONTYPE} Mode")
    return jsonify({ "success": True, "message": "" }) , 200
    
    
@app.route('/stop_session', methods=['POST'])
def stop_session():
    """
    Route to stop the current session.
    Receives: SessionID associated with the current session, route to where to upload the closing session's recorded footage
    {'SessionID': , 'uploading_route':}
    Returns: JSON containing a boolean to indicate success or not and in case of error an error message ("No Current Session", "Invalid SessionID", "Wrong SessionID", "Invalid Uploading Route") 
    {'success': , 'message': } 
    """ 
    
    if not request.is_json:
        return jsonify({"success": False, "message": "Invalid or missing JSON data"}), 400
    
    if not verifyAuthentication(request):
        return jsonify({"success": False, "message": "Wrong or None Authorization Header"}), 401
    
    SessionID = request.json.get('SessionID', -1)
    UPLOADURL = request.json.get('uploading_route', -1)
    
    # ADD UPLOADING ROUTE VALIDATION
    
    if webapp.SessionID == -1:
        print("No Current Session to Stop")
        return jsonify({ "success": False, "message": "No Current Session" }), 200
    if not validID(SessionID):
        print("Can't Stop Invalid SessionID")
        return jsonify({ "success": False, "message": "Invalid SessionID" }), 200
    if SessionID != webapp.SessionID:
        print("Can't Stop Wrong SessionID")
        return jsonify({ "success": False, "message": "Wrong SessionID" }), 200
    if UPLOADURL == -1:
        print("Can't Stop Invalid or None Uploading Route")
        return jsonify({ "success": False, "message": "Invalid Uploading Route" }), 200
        
    # Stop the current session
    print(f"Stopping Session {webapp.SessionID} and uploading to {UPLOADURL} ")
    commands.tracking_enabled = False
    camera_state.enable_auto_recording = False
    webapp.SessionID = -1 
    webapp.uploading_route = UPLOADURL
    
    # Call the method for uploading the last sessions's footage to its respective URL
    
    return jsonify({ "success": True, "message": ""}), 200

@app.route('/check_status')
def check_status():
    """
    Route to check if the camera is available for working or if not, why
    Returns: JSON with a bool indicating if the camera is currently on a session or not. If it is, for how long (in seconds) and to who it belongs
    {'available': bool, 'message': str}
    """
    
    if not verifyAuthentication(request):
        return jsonify({"success": False, "message": "Wrong or None Authorization Header"}), 401
    
    if webapp.SessionID == -1 and webapp.ErrorStates == '':
        print("Camera is Available for Session")
        return jsonify({ "available": True}), 200
    if webapp.SessionID != -1:
        print("Camera isnt available, session already established")
        return jsonify({"available": False, 'message': 'Session Already Established'}), 200
    if webapp.ErrorStates != '':
        print(f"Camera isnt available: {webapp.ErrorStates}")
        return jsonify({'available': False, 'message': webapp.ErrorStates}), 200
    
    return jsonify({ "available": True}), 200

@app.route('/remote_reboot')
def remote_reboot():
    '''
    Route to force reboot the system in case of malfunctioning.
    '''
    
    if not verifyAuthentication(request):
        return jsonify({"success": False, "message": "Wrong or None Authorization Header"}), 401
    
    response = make_response(jsonify({"message": "Rebooting the system..."}), 200)

    import threading
    import os
    # Start a thread to delay the reboot, allowing the response to be sent first
    threading.Timer(1, os.system, args=['sudo reboot']).start()

    return response
    
def start_server():
    print("starting server")
    app.run(host="0.0.0.0", port="53111", threaded=True)

from multiprocessing import Process
import subprocess
p_server = Process(target=start_server)
p_server.start()

command = [
    'ngrok',
    'http', '--domain=useful-advanced-termite.ngrok-free.app', '53111'
]
#subprocess.run(command)
subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pass

p_server.terminate()
p_server.join()


