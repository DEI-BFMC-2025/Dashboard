import threading, time, cv2
from unix_components.unix_socket_camera import UnixSocketCamera

frame = None
cap = UnixSocketCamera(socket_addr="/tmp/bfmc_socket2.sock", frame_size=(320, 240))

def capture_frames():
    global frame
    while True:
        ret, frame = cap.read()
        time.sleep(0.03) # Adjustable

def generate_frames():
    global frame
    while True:
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03) # Adjustable

def start_video_capture():
    threading.Thread(target=capture_frames, daemon=True).start()
