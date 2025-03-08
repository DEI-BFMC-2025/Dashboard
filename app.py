import cv2 # type: ignore
import threading
import time
import subprocess
from flask import Flask, render_template, Response, jsonify
from unix_socket_camera import UnixSocketCamera
from socket_metrics_receive import MetricReceiver  # Import the new receiver

app = Flask(__name__)

# Global variables
frame = None
current_node = "Start"
next_event = "Move Forward"
metrics = {}  # Store metrics from the receiver
metrics_lock = threading.Lock()  # Thread-safe access to metrics

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
    print("Starting metric receiver...")  # Debugging
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

@app.route('/metrics')
def get_metrics():
    """Get the latest metrics from the receiver."""
    with metrics_lock:
        #print("Serving metrics:", metrics)  # Debugging
        return jsonify(metrics)

@app.route('/status')
def status():
    return jsonify({
        'current_node': current_node,
        'next_event': next_event
    })

@app.route('/run-ssh', methods=['POST'])
def run_ssh():
    """Execute an SSH command."""
    try:
        result = subprocess.run(["ls", "/home/pi/Desktop"], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        output = f"Error: {e}"
    return jsonify(output=output)

if __name__ == '__main__':
    app.run(host='192.168.1.50', port=5000, debug=False)