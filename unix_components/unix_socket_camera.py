#!/usr/bin/env python3
import socket
import os
import numpy as np
import cv2
import time
import signal

class UnixSocketCamera:
    def __init__(self, socket_addr="/tmp/bfmc_socket.sock", frame_size=(320, 240)):
        self.socket_addr = socket_addr
        self.frame_size = frame_size
        self.msg_size = frame_size[0] * frame_size[1] * 3
        self.sock = None
        self.conn = None
        self.data = b''
        self.retry_interval = 2  # seconds between connection attempts
        self.running = True

        # Signal handling setup
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.create_socket_server()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived shutdown signal ({signum}), initiating cleanup...")
        self.shutdown()

    def create_socket_server(self):
        # Cleanup existing socket file
        if os.path.exists(self.socket_addr):
            try:
                os.remove(self.socket_addr)
            except OSError as e:
                print(f"Error removing socket file: {e}")

        # Create new socket server
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(self.socket_addr)
            self.sock.listen(1)
            self.sock.settimeout(1)  # For periodic connection checks
            print(f"Socket server created at {self.socket_addr}")
        except socket.error as e:
            print(f"Socket creation error: {e}")
            self.sock = None

    def maintain_connection(self):
        """Handle connection establishment and reconnection"""
        while self.running and not self.conn:
            try:
                print("Waiting for camera container connection...")
                self.conn, _ = self.sock.accept()
                self.conn.settimeout(2)
                print("Camera container connected")
                self.data = b''  # Reset buffer for new connection
            except socket.timeout:
                continue  # Normal timeout for connection checks
            except (OSError, socket.error) as e:
                print(f"Connection error: {e}")
                time.sleep(self.retry_interval)
                self.recreate_socket()

    def recreate_socket(self):
        """Recreate the socket server if needed"""
        try:
            if self.sock:
                self.sock.close()
            self.create_socket_server()
        except Exception as e:
            print(f"Socket recreation failed: {e}")
            time.sleep(self.retry_interval)

    def read(self):
        if not self.conn:
            self.maintain_connection()
            return False, None

        try:
            # Attempt to read frame data
            while len(self.data) < self.msg_size:
                chunk = self.conn.recv(4096)
                if not chunk:  # Connection closed
                    raise ConnectionError("Camera container disconnected")
                self.data += chunk

            # Process complete frame
            frame_data = self.data[:self.msg_size]
            self.data = self.data[self.msg_size:]
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                self.frame_size[1], self.frame_size[0], 3
            )
            return True, frame

        except (ConnectionError, socket.timeout, socket.error) as e:
            print(f"Connection issue: {e}")
            self.cleanup_connection()
            return False, None

    def cleanup_connection(self):
        """Clean up existing connection and prepare for reconnect"""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
            self.conn = None

    def shutdown(self):
        """Controlled shutdown procedure"""
        if not self.running:
            return

        print("\nInitiating controlled shutdown...")
        self.running = False

        # Clean up connections
        self.cleanup_connection()

        # Close main socket
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                print(f"Error closing socket: {e}")

        # Remove socket file
        if os.path.exists(self.socket_addr):
            try:
                os.remove(self.socket_addr)
            except Exception as e:
                print(f"Error removing socket file: {e}")

        print("Camera socket resources cleaned up")

    def __del__(self):
        """Destructor for additional safety"""
        self.shutdown()

if __name__ == "__main__":
    cap = UnixSocketCamera(socket_addr="/tmp/bfmc_socket.sock", frame_size=(320, 240))
    
    try:
        while cap.running:  # Use the running flag as condition
            success, frame = cap.read()
            if success:
                cv2.imshow("Unix Socket Camera", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cap.shutdown()
                    break
            else:
                print("Waiting for connection or data...")
                time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received...")
    finally:
        cap.shutdown()
        cv2.destroyAllWindows()
        print("Clean shutdown completed")