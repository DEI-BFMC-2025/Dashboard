import threading, time
from unix_components.unix_socket_metrics import MetricReceiver
from unix_components.unix_socket_lidar import LidarReceiver

metrics = {}
metrics_lock = threading.Lock()
lidar_data = []
lidar_lock = threading.Lock()

metric_receiver = MetricReceiver(metrics, metrics_lock)
lidar_receiver = LidarReceiver(lidar_data, lidar_lock)

def broadcast_metrics(socketio):
    while True:
        with metrics_lock:
            socketio.emit('metrics_update', metrics)
        time.sleep(0.1) # Adjustable

def broadcast_lidar(socketio):
    while True:
        with lidar_lock:
            if lidar_data:
                socketio.emit('lidar_update', {'points': lidar_data}, namespace='/lidar')
        time.sleep(0.1) # Adjustable

def start_broadcast_threads(socketio):
    threading.Thread(target=metric_receiver.start, daemon=True).start()
    threading.Thread(target=lidar_receiver.start, daemon=True).start()

    threading.Thread(target=broadcast_metrics, args=(socketio,), daemon=True).start()
    threading.Thread(target=broadcast_lidar, args=(socketio,), daemon=True).start()

