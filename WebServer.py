import json
from flask import render_template, Flask, send_from_directory, Response, jsonify, request
from flask_cors import CORS
import time
import Zoom
import cv2 
import subprocess 
import db

def main(d):
    conn = db.get_connection()
    gps_points = db.GPSData(conn)
    commands = db.Commands(conn)
    camera_state = db.CameraState(conn)
    
    app = Flask(__name__)

    @app.route("/")
    def index():
        """Video streaming home page."""
        return render_template('index.html')

    @app.route('/start_recording', methods=["POST"])
    def start_recording():
        """Sets the db camera state to start recording"""
        print("---")
        print("Flask Start Recording")
        camera_state.start_recording = True
        return jsonify({ "success": camera_state.start_recording, "message": "OK" })

    @app.route('/stop_recording', methods=["POST"])
    def stop_recording():
        """Sets the db camera state to stop recording"""
        print("Flask Stop Recording")
        camera_state.start_recording = False
        return jsonify({ "success": camera_state.start_recording, "message": "OK" })
    
    @app.route('/enable_autorec', methods=["POST"])
    def enable_autorec():
        """Sets the db camera state to enable auto recording"""
        print("---")
        print("Flask Auto Recording")
        camera_state.enable_auto_recording = True
        return jsonify({ "success": camera_state.enable_auto_recording, "message": "OK" })
    
    @app.route('/disable_autorec', methods=["POST"])
    def disable_autorec():
        """Sets the db camera state to disable auto recording"""
        print("---")
        print("Flask Stop Auto Recording")
        camera_state.enable_auto_recording = False
        return jsonify({ "success": camera_state.enable_auto_recording, "message": "OK" })

    @app.route('/start_tracking', methods=["POST"])
    def start_tracking():
        """Start Tracking"""
        print("Flask Start Tracking")
        commands.tracking_enabled = True
        return jsonify({ "success": True, "message": "OK" })

    @app.route('/stop_tracking', methods=["POST"])
    def stop_tracking():
        """Put camera in idle mode."""
        print("Flask StopTracking")
        commands.tracking_enabled = False
        return jsonify({ "success": True, "message": "OK" })

    @app.route('/update_zoom_value', methods=["POST"])
    def update_zoom_value():
        zoom_val = request.json.get('zoom_value', 0)
        print(zoom_val)
        zoom_controller = Zoom.SoarCameraZoomFocus()
        zoom_controller.set_zoom_position(zoom_val)
        print("Flask Updating Zoom")
        return jsonify({"success": True, "message": "Values Updated!"})
    
    @app.route('/increment', methods=['POST'])
    def increment():
        gps_points.camera_heading_angle += 0.0174532925
        return jsonify({"success": True, "message": "Values Updated!"})

    @app.route('/decrement', methods=['POST'])
    def decrement():
        gps_points.camera_heading_angle -= 0.0174532925
        return jsonify({"success": True, "message": "Values Updated!"})

    @app.route('/tilt_offset_plus', methods=['POST'])
    def tilt_offset_plus():
        gps_points.tilt_offset += 0.25
        return jsonify({"success": True, "message": "Values Updated!"})

    @app.route('/tilt_offset_minus', methods=['POST'])
    def tilt_offset_minus():
        gps_points.tilt_offset -= 0.25
        return jsonify({"success": True, "message": "Values Updated!"})
    

    @app.route('/calibrate_position', methods=["POST"])
    def calibrate_position():
        """Triggers the calibration method for the camera origin"""
        print("flask calibrate_position")
        commands.camera_calibrate_origin = True
        return jsonify({ "success": True, "message": "OK" })

    @app.route('/calibrate_heading', methods=["POST"])
    def calibrate_heading():
        """Triggers the calibration method for the camera heading"""
        print("flask calibrate_heading")
        commands.camera_calibrate_heading = True
        return jsonify({ "success": True, "message": "OK" })

    
    def gen():
        """Video streaming generator function."""
        while True:
            yield camera_state.image
            time.sleep(0.15)
 
    @app.route('/video_feed')
    def video_feed():
        """Video streaming route. Put this in the src attribute of an img tag."""
        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/shutdown_surf')
    def shutdown_surf():
        """Route to shutdown system"""
        from subprocess import call
        import IOBoardDriver as IO
        frontboard = IO.FrontBoardDriver()
        frontboard.setShutdown(seconds=10)
        time.sleep(1)
        call("sudo shutdown -h now", shell=True)
        return jsonify({ "success": True, "message": "OK" })
    
    def start_server():
        print("starting server")
        app.run(host="0.0.0.0", port="5000", threaded=True)

    from multiprocessing import Process
    p_server = Process(target=start_server)
    p_server.start()
    try:
        while not d["stop"]:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    p_server.terminate()
    p_server.join()