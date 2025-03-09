#!/usr/bin/env python3
import socket
import json
import time
import random
import os

SOCKET_PATH = "/tmp/metrics_socket.sock"

# Possible values for testing
CHECKPOINTS = [455, 465, 99, 154, 192, 434, 500, 133, 91, 466, 323]
STATES = ["START_STATE", "END_STATE", "DOING_NOTHING", "LANE_FOLLOWING", "APPROACHING_STOPLINE", 
          "INTERSECTION_NAVIGATION", "GOING_STRAIGHT", "TRACKING_LOCAL_PATH", "ROUNDABOUT_NAVIGATION", 
          "WAITING_FOR_PEDESTRIAN", "WAITING_FOR_GREEN", "WAITING_AT_STOPLINE", "OVERTAKING_STATIC_CAR", 
          "OVERTAKING_MOVING_CAR", "TAILING_CAR", "AVOIDING_ROADBLOCK", "PARKING", "CROSSWALK_NAVIGATION", 
          "CLASSIFYING_OBSTACLE", "BRAINLESS"]
EVENTS = ["INTERSECTION_STOP_EVENT", "INTERSECTION_TRAFFIC_LIGHT_EVENT", "INTERSECTION_PRIORITY_EVENT", 
          "JUNCTION_EVENT", "ROUNDABOUT_EVENT", "CROSSWALK_EVENT", "PARKING_EVENT", "HIGHWAY_EXIT_EVENT", 
          "HIGHWAY_ENTRANCE_EVENT"]
ROUTINES = [
    ["FOLLOW_LANE", "UPDATE_STATE"], 
    ["FOLLOW_LANE", "DETECT_STOPLINE", "SLOW_DOWN", "CONTROL_FOR_SIGNS"],
    ["ACCELERATE", "CONTROL_FOR_SIGNS"],
    ["CONTROL_FOR_OBSTACLES", "UPDATE_STATE"],
    ["FOLLOW_LANE", "DRIVE_DESIRED_SPEED", "UPDATE_STATE"]
]
CONDITIONS = [
    {"CAN_OVERTAKE": False, "HIGHWAY": True, "REROUTING": True, "NO_LANE": True,"TRUST_GPS": True, "CAR_ON_PATH": False},
    {"CAN_OVERTAKE": True, "HIGHWAY": False, "REROUTING": False, "NO_LANE": True,"TRUST_GPS": False, "CAR_ON_PATH": True},
    {"CAN_OVERTAKE": False, "HIGHWAY": True, "REROUTING": False, "NO_LANE": False,"TRUST_GPS": True, "CAR_ON_PATH": True},
    {"CAN_OVERTAKE": True, "HIGHWAY": False, "REROUTING": True, "NO_LANE": False,"TRUST_GPS": False, "CAR_ON_PATH": False}
]

def generate_metrics():
    """Generate random metrics for testing."""
    return {
        "CHECKPOINT": random.choice(CHECKPOINTS),
        "STATE": random.choice(STATES),
        "PREV_EVENT": random.choice(EVENTS + [None]),
        "UPCOMING_EVENT": random.choice(EVENTS),
        "ROUTINES": random.choice(ROUTINES),
        "CONDITIONS": random.choice(CONDITIONS),
        "SPEED": round(random.uniform(0.0, 10.0), 2),
        "STEER": round(random.uniform(-5.0, 5.0), 2),
        "DISTANCE": round(random.uniform(0.0, 100.0), 2),
        "SONAR_L": round(random.uniform(0.0, 50.0), 2),
        "SONAR_R": round(random.uniform(0.0, 50.0), 2),
        "SONAR_C": round(random.uniform(0.0, 50.0), 2),
        "YAW": round(random.uniform(-180.0, 180.0), 2),
        "HEADING": random.choice(["NORTH", "EAST", "SOUTH", "WEST"]),
    }

class MetricSender:
    def __init__(self):
        self.sock = None
        self.connected = False

    def connect_to_server(self):
        """Continuously attempt to connect to the receiver."""
        while True:
            try:
                if os.path.exists(SOCKET_PATH):
                    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.sock.connect(SOCKET_PATH)
                    self.connected = True
                    print("Connected to receiver.")
                    break  # Exit the loop on successful connection
                else:
                    print("Socket file does not exist. Waiting for receiver...")
                    time.sleep(2)
            except (FileNotFoundError, ConnectionRefusedError):
                print("Waiting for receiver...")
                time.sleep(2)
            except Exception as e:
                print(f"Connection error: {e}")
                time.sleep(2)

    def send_metrics(self, metrics):
        """
        Send metrics to the receiver.

        Args:
            metrics (dict): A dictionary containing the metrics to send.

        Returns:
            bool: True if metrics were sent successfully, False otherwise.
        """
        if not self.connected:
            print("Not connected to receiver.")
            self.connect_to_server()  # Attempt to reconnect
            return False

        try:
            if not isinstance(metrics, dict):
                print("Metrics must be a dictionary.")
                return False

            data = json.dumps(metrics).encode('utf-8') + b'\n'  # Add newline separator
            self.sock.sendall(data)
            #print(f"Sent metrics: {metrics}")
            return True
        except (BrokenPipeError, ConnectionRefusedError):
            print("Connection lost. Attempting to reconnect...")
            self.connected = False
            self.connect_to_server()  # Reconnect
            return False
        except Exception as e:
            print(f"Error sending metrics: {e}")
            return False

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
        # Do not remove the socket file, since the receiver might still be running.
        self.connected = False
        print("Connection closed.")


if __name__ == "__main__":
    sender = MetricSender()
    sender.connect_to_server()  # Connect to the receiver

    try:
        while True:  # Main loop
            # Generate random metrics for testing
            metrics = generate_metrics()

            # Send metrics
            if sender.send_metrics(metrics):
                time.sleep(random.uniform(0.5, 2.0))  # Random delay between sends
    except KeyboardInterrupt:
        print("\nShutting down producer...")
    finally:
        sender.close()