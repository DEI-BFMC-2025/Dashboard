from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import paramiko
from unix_socket_camera import UnixSocketCamera
from socket_metrics_receive import MetricReceiver
from unix_socket_lidar import LidarReceiver
import time
import cv2
import os
import pty
import select

app = Flask(__name__)
socketio = SocketIO(app)

# SSH Configuration
HOSTNAME = "10.144.105.55"
USERNAME = "eugen"
PASSWORD = "gradenigo6"
SCRIPT_PATH = "/home/eugen/Desktop/FlaskWebApp/looping.py"
SCRIPT_NAME = "looping.py"




COMMANDS = {
    "brain": {
        "start": "mkdir /home/eugen/Desktop/MyFolder",
        "stop": "mkdir /home/eugen/Desktop/MyFolder2"
    },
    "camera": {
        "start": "python3 /path/to/camera_script.py",
        "stop": "pkill -f camera_script.py"
    },
    "imu": {
        "start": "python3 /path/to/imu_script.py",
        "stop": "pkill -f imu_script.py"
    }
}





# Global variables
frame = None
metrics = {}
metrics_lock = threading.Lock()
lidar_data = []
lidar_lock = threading.Lock()

# Initialize components
cap = UnixSocketCamera(socket_addr="/tmp/bfmc_socket2.sock", frame_size=(320, 240))
metric_receiver = MetricReceiver(metrics, metrics_lock)
lidar_receiver = LidarReceiver(lidar_data, lidar_lock)

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
threading.Thread(target=lidar_receiver.start, daemon=True).start()

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







def execute_ssh_command(command):
    """Execute a command via SSH and return the result."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        ssh.close()
        return {"success": True, "output": output, "error": error}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/control/<system>/<action>', methods=['POST'])
def control_system(system, action):
    """Control a system (brain/camera/imu) with start/stop actions."""
    if system not in COMMANDS or action not in ["start", "stop"]:
        return jsonify(success=False, message="Invalid system or action")
    
    command = COMMANDS[system][action]
    result = execute_ssh_command(command)
    
    if result["success"]:
        if result["error"]:
            return jsonify(success=True, message=f"Command executed with warnings: {result['error']}")
        return jsonify(success=True, message=f"{system.capitalize()} {action}ed successfully")
    else:
        return jsonify(success=False, message=f"Failed to {action} {system}: {result['error']}")




@socketio.on('terminal_input')
def handle_terminal_input(data):
    if not hasattr(handle_terminal_input, "fd"):
        # Spawn a pseudo-terminal for the shell
        pid, fd = pty.fork()
        if pid == 0:
            # Child process - start the shell
            os.execvp("bash", ["bash"])
        else:
            # Parent process - store the file descriptor
            handle_terminal_input.fd = fd
            threading.Thread(target=forward_output, args=(fd,), daemon=True).start()
    
    # Send input to the process
    os.write(handle_terminal_input.fd, data.encode())

def forward_output(fd):
    while True:
        r, _, _ = select.select([fd], [], [])
        if fd in r:
            try:
                data = os.read(fd, 1024)
                socketio.emit('terminal_output', data.decode())
            except OSError:
                # Terminal closed
                del handle_terminal_input.fd
                break


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

@socketio.on('connect', namespace='/lidar')
def handle_lidar_connect():
    with lidar_lock:
        emit('lidar_update', {'points': lidar_data})

def broadcast_lidar():
    """Broadcast LIDAR data to all connected clients."""
    while True:
        with lidar_lock:
            if lidar_data:  # Only send if we have data
                socketio.emit('lidar_update', {'points': lidar_data}, namespace='/lidar')
        time.sleep(0.1)  # Faster update for LIDAR

# Start the metrics broadcast thread
threading.Thread(target=broadcast_metrics, daemon=True).start()
threading.Thread(target=broadcast_lidar, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host=HOSTNAME, port=5000, debug=False, allow_unsafe_werkzeug=True)