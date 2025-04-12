import paramiko

USERNAME = "eugen"
PASSWORD = "gradenigo6"
HOSTNAME = "localhost"

COMMANDS = {
    "brain": {"start": "python3 /path/to/brain_script.py", "stop": "soft_exit"},
    "camera": {"start": "python3 /path/to/camera_script.py", "stop": "soft_exit"},
    "imu": {"start": "python3 /path/to/imu_script.py", "stop": "soft_exit"}
}

process_tracker = {k: {"pid": None, "channel": None} for k in COMMANDS}

def execute_ssh_command(command, system=None, action=None):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)

        if action == "start" and system:
            transport = ssh.get_transport()
            channel = transport.open_session()
            channel.exec_command(f"nohup {command} > /dev/null 2>&1 & echo $!")
            pid = channel.recv(1024).decode().strip()
            process_tracker[system].update({"pid": pid, "channel": channel})
            return {"success": True, "pid": pid}
        elif action == "stop" and system:
            pid = process_tracker[system]["pid"]
            if pid:
                ssh.exec_command(f"kill -2 {pid}")
                process_tracker[system]["pid"] = None
                return {"success": True}

        stdin, stdout, stderr = ssh.exec_command(command)
        return {
            "success": True,
            "output": stdout.read().decode(),
            "error": stderr.read().decode()
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if 'ssh' in locals():
            ssh.close()
