from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO
from video_stream import generate_frames, start_video_capture
from broadcast import start_broadcast_threads
from socket_handlers import init_socket_handlers
from ssh_utils import execute_ssh_command, COMMANDS

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control/<system>/<action>', methods=['POST'])
def control_system(system, action):
    # Check if system exists in COMMANDS
    if system not in COMMANDS:
        return jsonify(success=False, message="Invalid system")
    # Check if action is valid for this system
    if action not in COMMANDS[system]:
        return jsonify(success=False, message=f"Invalid action '{action}' for system '{system}'")
    # Get the command (handle soft_exit specially)
    command = COMMANDS[system][action]

    # Execute the command
    result = execute_ssh_command(command, system, action)
    if result["success"]:
        message = result.get("message", f"{system.capitalize()} {action}ed successfully")
        return jsonify(success=True, message=message)
    return jsonify(success=False, message=f"Failed to {action} {system}: {result.get('error', 'Unknown error')}")

# Start background processes
start_video_capture()
start_broadcast_threads(socketio)
init_socket_handlers(socketio)

if __name__ == '__main__':
    socketio.run(app, host='10.144.105.55', port=5000, debug=False, allow_unsafe_werkzeug=True)
