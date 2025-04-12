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
USERNAME = "eugen"
PASSWORD = "gradenigo6"
HOSTNAME = "localhost"

COMMANDS = {
    "brain": {
        "start": "python3 /path/to/brain_script.py",
        "stop": "soft_exit"  # is a special flag for the handler
    },
    "camera": {
        "start": "python3 /path/to/camera_script.py",
        "stop": "soft_exit"
    },
    "imu": {
        "start": "python3 /path/to/imu_script.py",
        "stop": "soft_exit"
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

# Global variable to track running processes
process_tracker = {
    "camera": {"pid": None, "channel": None},
    "imu": {"pid": None, "channel": None},
    "brain": {"pid": None, "channel": None}
}

def execute_ssh_command(command, system=None, action=None):
    """Execute a command via SSH and track processes"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
        
        if action == "start" and system:
            # Start process in background and get PID
            transport = ssh.get_transport()
            channel = transport.open_session()
            channel.exec_command(f"nohup {command} > /dev/null 2>&1 & echo $!")
            
            # Get PID from stdout
            pid = channel.recv(1024).decode().strip()
            process_tracker[system]["pid"] = pid
            process_tracker[system]["channel"] = channel
            
            return {"success": True, "pid": pid}
            
        elif action == "stop" and system:
            # Send SIGINT (CTRL+C equivalent)
            pid = process_tracker[system]["pid"]
            if pid:
                stdin, stdout, stderr = ssh.exec_command(f"kill -2 {pid}")
                process_tracker[system]["pid"] = None
                return {"success": True}
            
        # Fallback for regular commands
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        return {"success": True, "output": output, "error": error}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'ssh' in locals():
            ssh.close()

@app.route('/control/<system>/<action>', methods=['POST'])
def control_system(system, action):
    """Enhanced system control with soft termination"""
    if system not in COMMANDS or action not in ["start", "stop"]:
        return jsonify(success=False, message="Invalid system or action")
    
    command = COMMANDS[system][action]
    
    # Handle soft exit for stop command
    if action == "stop" and command == "soft_exit":
        result = execute_ssh_command("", system, "stop")
    else:
        result = execute_ssh_command(command, system, action)
    
    if result["success"]:
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
            if lidar_data:  # send only if we have data
                socketio.emit('lidar_update', {'points': lidar_data}, namespace='/lidar')
        time.sleep(0.1)     # update rate

# Start the metrics broadcast thread
threading.Thread(target=broadcast_metrics, daemon=True).start()
threading.Thread(target=broadcast_lidar, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host=HOSTNAME, port=5000, debug=False, allow_unsafe_werkzeug=True)