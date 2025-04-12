#!/usr/bin/env python3
import socket
import json
import os
import signal
import time
from threading import Lock, Thread

SOCKET_PATH = "/tmp/lidar_socket.sock"

class LidarReceiver:
    def __init__(self, lidar_data, lidar_lock):
        self.lidar_data = lidar_data
        self.lidar_lock = lidar_lock
        self.running = True
        self.buffer = b''
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        print("\nShutting down LIDAR receiver...")
        self.running = False
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        exit(0)

    def start(self):
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)
        server.settimeout(1.0)
        print(f"LIDAR listening on {SOCKET_PATH}...")

        while self.running:
            try:
                conn, _ = server.accept()
                print("LIDAR producer connected!")
                conn.settimeout(1.0)

                while self.running:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        self.buffer += chunk

                        while b'\n' in self.buffer:
                            line, self.buffer = self.buffer.split(b'\n', 1)
                            try:
                                points = json.loads(line)
                                with self.lidar_lock:
                                    self.lidar_data.clear()
                                    self.lidar_data.extend(points)
                            except json.JSONDecodeError:
                                print(f"Invalid LIDAR data: {line}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"LIDAR connection error: {e}")
                        break
            except socket.timeout:
                continue
            except Exception as e:
                print(f"LIDAR server error: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()
                self.buffer = b''

        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

if __name__ == "__main__":
    lidar_data = []
    lidar_lock = Lock()

    receiver = LidarReceiver(lidar_data, lidar_lock)

    def printer():
        while True:
            with lidar_lock:
                if lidar_data:
                    print(f"Received {len(lidar_data)} points, sample: {lidar_data[:3]}")
            time.sleep(1)

    Thread(target=printer, daemon=True).start()
    receiver.start()
