import cv2                                          # type: ignore
import time
from socket_metrics_receive import MetricReceiver  
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit           # type: ignore
import threading
import paramiko                                     # type: ignore
from unix_socket_camera import UnixSocketCamera


app = Flask(__name__)
socketio = SocketIO(app)

# SSH Configuration
HOSTNAME = "192.168.1.50"
USERNAME = "pi"
PASSWORD = "gradenigo6"
SCRIPT_PATH = "/home/pi/Desktop/FlaskWebApp/looping.py"
SCRIPT_NAME = "looping.py"

# Global variables
frame = None
metrics = {}
metrics_lock = threading.Lock()

# Initialize components
cap = UnixSocketCamera(socket_addr="/tmp/bfmc_socket.sock", frame_size=(320, 240))
metric_receiver = MetricReceiver(metrics, metrics_lock)

def capture_frames():
    global frame
    while True:
        ret, frame = cap.read()
        time.sleep(0.03)

def run_metric_receiver():
    """Run the metric receiver in the background."""
    print("Starting metric receiver...")
    metric_receiver.start()

# Start background threads
threading.Thread(target=capture_frames, daemon=True).start()
threading.Thread(target=run_metric_receiver, daemon=True).start()

def generate_frames():
    global frame
    while True:
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_script', methods=['POST'])
def start_script():
    """Start the script via SSH."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        ssh.exec_command(f"nohup python3 {SCRIPT_PATH} > /dev/null 2>&1 &")
        ssh.close()
        return jsonify(success=True, message="Script started")
    except Exception as e:
        return jsonify(success=False, message=str(e))

@app.route('/stop_script', methods=['POST'])
def stop_script():
    """Stop the script via SSH."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        ssh.exec_command(f"pkill -f {SCRIPT_NAME}")
        ssh.close()
        return jsonify(success=True, message="Script stopped")
    except Exception as e:
        return jsonify(success=False, message=str(e))
    
@app.route('/run_custom_script', methods=['POST'])
def run_custom_script():
    """Run a custom script via SSH."""
    try:
        # Get the custom script from the request
        data = request.get_json()
        script = data.get('script')
        if not script:
            return jsonify(success=False, message="No script provided")

        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)

        # Execute the custom script
        stdin, stdout, stderr = ssh.exec_command(script)
        output = stdout.read().decode()
        error = stderr.read().decode()

        # Close the SSH connection
        ssh.close()

        # Check for errors
        if error:
            return jsonify(success=False, message=f"Error executing script: {error}")

        return jsonify(success=True, message="Custom script executed", output=output)

    except Exception as e:
        return jsonify(success=False, message=str(e))

@app.route('/stop_custom_script', methods=['POST'])
def stop_custom_script():
    """Stop the custom script via SSH."""
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)

        # Kill the custom script process
        stdin, stdout, stderr = ssh.exec_command("pkill -f custom_script")
        output = stdout.read().decode()
        error = stderr.read().decode()

        # Close the SSH connection
        ssh.close()

        # Check for errors
        if error:
            return jsonify(success=False, message=f"Error stopping script: {error}")

        return jsonify(success=True, message="Custom script stopped", output=output)

    except Exception as e:
        return jsonify(success=False, message=str(e))

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    with metrics_lock:
        socketio.emit('metrics_update', metrics)

def broadcast_metrics():
    """Broadcast metrics to all connected clients."""
    while True:
        with metrics_lock:
            socketio.emit('metrics_update', metrics)
        time.sleep(1)

# Start the metrics broadcast thread
threading.Thread(target=broadcast_metrics, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host='192.168.1.50', port=5000, debug=False)