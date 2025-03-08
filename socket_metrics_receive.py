#!/usr/bin/env python3
import socket
import json
import os
import signal
from threading import Lock

SOCKET_PATH = "/tmp/metrics_socket.sock"

class MetricReceiver:
    def __init__(self, metrics, metrics_lock):
        self.metrics = metrics  # Shared metrics dictionary
        self.metrics_lock = metrics_lock  # Thread-safe lock
        self.running = True
        self.buffer = b''
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        print("\nShutting down receiver...")
        self.running = False
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        exit(0)

    def format_metrics(self, metrics):
        """Format metrics for display (optional)."""
        output = []
        output.append(f"CHECKPOINT: {metrics.get('CHECKPOINT', '')}")
        output.append(f"STATE: {metrics.get('STATE', '')}")
        output.append(f"PREV EVENT: {metrics.get('PREV_EVENT', '')}")
        output.append(f"NEXT EVENT: {metrics.get('UPCOMING_EVENT', '')}")

        output.append("ROUTINES:")
        for routine in metrics.get('ROUTINES', []):
            output.append(f"  - {routine}")

        output.append("CONDITIONS:")
        for condition, value in metrics.get('CONDITIONS', {}).items():
            output.append(f"  {condition}: {value}")

        return "\n".join(output)


    def start(self):
        """Start the metric receiver server."""
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)
        print(f"Listening on {SOCKET_PATH}...")

        while self.running:
            try:
                conn, _ = server.accept()
                print("Producer connected!")
                conn.settimeout(1.0)  # Timeout for receive operations
                
                while self.running:
                    try:
                        chunk = conn.recv(1024)
                        if not chunk:
                            break
                            
                        self.buffer += chunk
                        
                        # Process complete messages (separated by \n)
                        while b'\n' in self.buffer:
                            line, self.buffer = self.buffer.split(b'\n', 1)
                            try:
                                metrics = json.loads(line)
                                #print("\nReceived metrics:", metrics)   # Debugging
                                with self.metrics_lock:                 # Thread-safe update
                                    self.metrics.update(metrics)        # Update shared metrics
                            except json.JSONDecodeError:
                                print(f"Invalid JSON: {line}")
                                
                    except socket.timeout:
                        continue  # Normal timeout for shutdown checks
                        
            except Exception as e:
                print(f"Connection error: {e}")
            finally:
                if 'conn' in locals():
                    conn.close()
                self.buffer = b''

        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

if __name__ == "__main__":
    # For standalone testing
    metrics = {}  # Shared metrics dictionary
    metrics_lock = Lock()  # Thread-safe lock
    receiver = MetricReceiver(metrics, metrics_lock)
    receiver.start()