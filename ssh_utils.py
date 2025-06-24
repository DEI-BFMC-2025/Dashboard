import paramiko

USERNAME = "eugen"
PASSWORD = "gradenigo6"
#HOSTNAME = "10.144.105.55"
#HOSTNAME = "192.168.50.173" COMPETITION
HOSTNAME = "192.168.43.74"
#HOSTNAME = "172.20.10.4"



COMMANDS = {
    "utils": {
        "start": "docker exec bfmc2025_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && roslaunch utils run_automobile_2024.launch'",
        "stop":  "docker exec bfmc2025_container pkill -2 -f run_automobile_2024.launch"
    },
    "brain": {
        "start": "docker exec bfmc2025_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && python3 main_brain.py'",
        "stop":  "docker exec bfmc2025_container pkill -2 -f main_brain.py"
    },
    "brain_random": {
        "start": "docker exec bfmc2025_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && python3 main_brain.py --random'",
        "stop":  "docker exec bfmc2025_container pkill -2 -f main_brain.py"
    },
    "brain_joy": {
        "start": "docker exec bfmc2025_container bash -c 'source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && python3 main_brain.py --resume'",
        "stop":  "docker exec bfmc2025_container pkill -2 -f main_brain.py"
    },
    "camera": {
        "restart": "sudo systemctl restart camera"
    },
    "dashboard": {
        "restart": "sudo systemctl restart dashboard"
    },
    "docker": {
        "restart": "cd /home/eugen/Desktop/Docker/raspberry && docker compose down && docker compose up -d"
    },
    "imu": {
        "restart": "sudo systemctl restart imu.service"
    }
}


process_tracker = {k: {"pid": None, "channel": None} for k in COMMANDS}

def execute_ssh_command(command, system=None, action=None):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)

        #if action in ["start"] and system:
        #    transport = ssh.get_transport()
        #    channel = transport.open_session()
        #    channel.exec_command(f"nohup {command} > /dev/null 2>&1 & echo $!")
        #    pid = channel.recv(1024).decode().strip()
        #    process_tracker[system].update({"pid": pid, "channel": channel})
        #    return {"success": True, "pid": pid}
        #elif action == "stop" and system:
        #    pid = process_tracker[system]["pid"]
        #    if pid:
        #        ssh.exec_command(f"kill -2 {pid}")
        #        process_tracker[system]["pid"] = None
        #        return {"success": True}
        #    
        #else:
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        #print("STDOUT:", output)
        #print("STDERR:", error)
        return {
            "success": True,
            "message": output if output else "Command executed successfully",
            "error": error
        }


    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'ssh' in locals():
            ssh.close()
