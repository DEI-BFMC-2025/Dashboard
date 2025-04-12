import os, pty, select, threading
from flask_socketio import emit

terminal_fd = {}

def init_socket_handlers(socketio):

    @socketio.on('terminal_input')
    def handle_terminal_input(data):
        if 'fd' not in terminal_fd:
            pid, fd = pty.fork()
            if pid == 0:
                os.execvp("bash", ["bash"])
            else:
                terminal_fd['fd'] = fd
                threading.Thread(target=forward_output, args=(fd, socketio), daemon=True).start()
        os.write(terminal_fd['fd'], data.encode())

    def forward_output(fd, socketio):
        while True:
            r, _, _ = select.select([fd], [], [])
            if fd in r:
                try:
                    data = os.read(fd, 1024)
                    socketio.emit('terminal_output', data.decode())
                except OSError:
                    terminal_fd.clear()
                    break

    @socketio.on('connect')
    def handle_connect():
        print("Client connected")
        from broadcast import metrics, metrics_lock
        with metrics_lock:
            emit('metrics_update', metrics)

    @socketio.on('connect', namespace='/lidar')
    def handle_lidar_connect():
        from broadcast import lidar_data, lidar_lock
        with lidar_lock:
            emit('lidar_update', {'points': lidar_data})
