from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO
from video_stream import generate_frames, start_video_capture
from broadcast import start_broadcast_threads
from socket_handlers import init_socket_handlers
from ssh_utils import execute_ssh_command, COMMANDS

app = Flask(__name__)
socketio = SocketIO(app)

# Start background processes
start_video_capture()
start_broadcast_threads(socketio)
init_socket_handlers(socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control/<system>/<action>', methods=['POST'])
def control_system(system, action):
    if system not in COMMANDS or action not in ["start", "stop"]:
        return jsonify(success=False, message="Invalid system or action")
    
    command = COMMANDS[system][action]
    result = execute_ssh_command("" if command == "soft_exit" else command, system, action)

    if result["success"]:
        return jsonify(success=True, message=f"{system.capitalize()} {action}ed successfully")
    return jsonify(success=False, message=f"Failed to {action} {system}: {result['error']}")

if __name__ == '__main__':
    socketio.run(app, host='localhost', port=5000, debug=False, allow_unsafe_werkzeug=True)
