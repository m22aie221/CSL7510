import socket
import threading
import time
import psutil
import subprocess
import os

BACKEND_IP = "127.0.0.1"
BACKEND_PORT = 9000
FRONTEND_PORT = 8000
CPU_THRESHOLD = 75.0
CPU_DOWNSCALE_THRESHOLD = 75.0


global active_backend
active_backend = "local"
switch_lock = threading.Lock()

# Set project files directory and GCP home directory dynamically
PROJECT_DIR = os.getcwd()
GCP_HOME_DIR = "$(echo $HOME)"


def instance_exists(instance_name):
    try:
        result = subprocess.run(["gcloud", "compute", "instances", "describe", instance_name, "--zone=us-central1-a"],
                                capture_output=True, text=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def configure_ssh_keys():
    try:
        print("Configuring SSH keys in project metadata...")
        subprocess.run(["gcloud", "compute", "project-info", "add-metadata",
                        "--metadata-from-file", "ssh-keys=" + os.path.expanduser("~/.ssh/google_compute_engine.pub")], check=True)
        print("SSH keys configured successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to configure SSH keys. Please check your setup.", str(e))


def create_firewall_rule():
    try:
        print("Creating firewall rule for backend server on port 9000...")
        subprocess.run([
            "gcloud", "compute", "firewall-rules", "create", "allow-backend-9000",
            "--allow", "tcp:9000",
            "--source-ranges", "0.0.0.0/0",
            "--target-tags", "backend-server",
            "--description", "Allow incoming traffic on port 9000 for backend server"
        ], check=True)
        print("Firewall rule created successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to create firewall rule:", str(e))

def add_network_tag():
    try:
        print("Adding network tag to GCP instance...")
        subprocess.run([
            "gcloud", "compute", "instances", "add-tags", "ondemand-vm2",
            "--zone=us-central1-a",
            "--tags=backend-server"
        ], check=True)
        print("Network tag added successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to add network tag:", str(e))

def get_gcp_ip():
    try:
        ip_result = subprocess.check_output(["gcloud", "compute", "instances", "describe", "ondemand-vm2", "--zone=us-central1-a", "--format=get(networkInterfaces[0].accessConfigs[0].natIP)"])
        return ip_result.decode().strip()
    except subprocess.CalledProcessError as e:
        print("Failed to get GCP instance IP:", str(e))
        return None

def scale_up2():
    global BACKEND_IP, active_backend
    print("[Scaling] Initiating GCP instance startup...")
    try:
        # Start the GCP instance
        subprocess.run(["gcloud", "compute", "instances", "start", "ondemand-vm2", "--zone=us-central1-a"], check=True)
        print("[Scaling] GCP instance started successfully.")

        # Wait for SSH to become available
        print("[Scaling] Waiting for SSH to become available...")
        max_retries = 10
        retry_delay = 5
        for attempt in range(max_retries):
            ssh_check = subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--command", "echo SSH is ready"
            ], capture_output=True, text=True)
            if ssh_check.returncode == 0:
                print("[Scaling] SSH is ready.")
                break
            print(f"[Scaling] SSH not ready (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("[Scaling] SSH did not become ready after multiple attempts. Aborting scale-up.")
            return

        # Transfer BackendServer.py to GCP instance
        print("[Scaling] Copying BackendServer.py to GCP instance...")
        try:
            subprocess.run([
                "gcloud", "compute", "scp", f"{PROJECT_DIR}/BackendServer.py",
                "ondemand-vm2:/tmp/BackendServer.py", "--zone=us-central1-a"
            ], check=True)
            print("[Scaling] BackendServer.py transferred successfully.")
        except subprocess.CalledProcessError as e:
            print("[Scaling] Error transferring BackendServer.py:", str(e))
            return

        # Start the backend server on GCP
        print("[Scaling] Starting backend server on GCP...")
        try:
            start_command = (
                "nohup python3 /tmp/BackendServer.py > /tmp/backend.log 2>&1 &"
            )
            subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--command", start_command
            ], check=True)
            print("[Scaling] Backend server started on GCP.")

            # Verify that the backend server is actually running
            print("[Scaling] Verifying backend server on GCP...")
            time.sleep(5)  # Give some time for the server to start
            verify = subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--",
                "pgrep -fl BackendServer.py"
            ], capture_output=True, text=True)
            if verify.returncode == 0:
                print("[Scaling] GCP backend server is running.")
                gcp_ip = get_gcp_ip()
                if gcp_ip:
                    with switch_lock:
                        print("[Scaling] Switching to GCP backend...")
                        BACKEND_IP = gcp_ip
                        active_backend = "gcp"
                        print(f"[Scaling] Successfully switched to GCP backend at {BACKEND_IP}")
                else:
                    print("[Scaling] Failed to retrieve GCP IP.")
            else:
                print("[Scaling] Backend server did not start on GCP. Checking logs:")
                log_check = subprocess.run([
                    "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--",
                    "tail -n 20 /tmp/backend.log"
                ], capture_output=True, text=True)
                print("[Scaling] Backend server logs:\n", log_check.stdout)
        except subprocess.CalledProcessError as e:
            print("[Scaling] Failed to start backend server on GCP:", str(e))
    except subprocess.CalledProcessError as e:
        print("[Scaling] Error during GCP scaling:", str(e))


def scale_up():
    global BACKEND_IP, active_backend
    print("[Scaling] Initiating GCP instance startup...")
    try:
        # Check if the GCP instance already exists
        if not instance_exists("ondemand-vm2"):
            print("[Scaling] Instance does not exist. Creating a new instance...")
            try:
                subprocess.run([
                    "gcloud", "compute", "instances", "create", "ondemand-vm2",
                    "--zone=us-central1-a",
                    "--machine-type=e2-medium",
                    "--image-family=ubuntu-2004-lts",
                    "--image-project=ubuntu-os-cloud",
                    "--tags=backend-server"
                ], check=True)
                print("[Scaling] GCP instance created successfully.")
                
                # Configure SSH keys
                configure_ssh_keys()

                # Create firewall rule
                create_firewall_rule()

                # Add network tag
                add_network_tag()
            except subprocess.CalledProcessError as e:
                print("[Scaling] Error creating GCP instance:", str(e))
                return
        else:
            print("[Scaling] Instance already exists. Starting...")
            subprocess.run(["gcloud", "compute", "instances", "start", "ondemand-vm2", "--zone=us-central1-a"], check=True)
            print("[Scaling] GCP instance started successfully.")

        # Wait for SSH to become available
        print("[Scaling] Waiting for SSH to become available...")
        max_retries = 10
        retry_delay = 5
        for attempt in range(max_retries):
            ssh_check = subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--command", "echo SSH is ready"
            ], capture_output=True, text=True)
            if ssh_check.returncode == 0:
                print("[Scaling] SSH is ready.")
                break
            print(f"[Scaling] SSH not ready (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("[Scaling] SSH did not become ready after multiple attempts. Aborting scale-up.")
            return

        # Transfer BackendServer.py to GCP instance
        print("[Scaling] Copying BackendServer.py to GCP instance...")
        try:
            subprocess.run([
                "gcloud", "compute", "scp", f"{PROJECT_DIR}/BackendServer.py",
                "ondemand-vm2:/tmp/BackendServer.py", "--zone=us-central1-a"
            ], check=True)
            print("[Scaling] BackendServer.py transferred successfully.")
        except subprocess.CalledProcessError as e:
            print("[Scaling] Error transferring BackendServer.py:", str(e))
            return

        # Start the backend server on GCP
        print("[Scaling] Starting backend server on GCP...")
        try:
            start_command = (
                "nohup python3 /tmp/BackendServer.py > /tmp/backend.log 2>&1 &"
            )
            subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--command", start_command
            ], check=True)
            print("[Scaling] Backend server started on GCP.")

            # Verify that the backend server is actually running
            print("[Scaling] Verifying backend server on GCP...")
            time.sleep(5)  # Give some time for the server to start
            verify = subprocess.run([
                "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--",
                "pgrep -fl BackendServer.py"
            ], capture_output=True, text=True)
            if verify.returncode == 0:
                print("[Scaling] GCP backend server is running.")
                gcp_ip = get_gcp_ip()
                if gcp_ip:
                    with switch_lock:
                        print("[Scaling] Switching to GCP backend...")
                        BACKEND_IP = gcp_ip
                        active_backend = "gcp"
                        print(f"[Scaling] Successfully switched to GCP backend at {BACKEND_IP}")
                else:
                    print("[Scaling] Failed to retrieve GCP IP.")
            else:
                print("[Scaling] Backend server did not start on GCP. Checking logs:")
                log_check = subprocess.run([
                    "gcloud", "compute", "ssh", "ondemand-vm2", "--zone=us-central1-a", "--",
                    "tail -n 20 /tmp/backend.log"
                ], capture_output=True, text=True)
                print("[Scaling] Backend server logs:\n", log_check.stdout)
        except subprocess.CalledProcessError as e:
            print("[Scaling] Failed to start backend server on GCP:", str(e))
    except subprocess.CalledProcessError as e:
        print("[Scaling] Error during GCP scaling:", str(e))



def scale_down():
    global BACKEND_IP, active_backend
    print("[Scaling] Initiating scale-down to local backend...")

    # Step 1: Switch to local backend before stopping GCP instance
    with switch_lock:
        BACKEND_IP = "127.0.0.1"
        active_backend = "local"
        print(f"[Scaling] Switched to local backend at {BACKEND_IP}")

    # Step 2: Stop the GCP instance
    print("[Scaling] Stopping GCP instance...")
    try:
        subprocess.run(["gcloud", "compute", "instances", "stop", "ondemand-vm2", "--zone=us-central1-a"], check=True)
        print("[Scaling] GCP instance stopped successfully.")
    except subprocess.CalledProcessError as e:
        print("[Scaling] Error during GCP scale-down:", str(e))


def monitor_cpu():
    global active_backend
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        print("[CPU Monitor] CPU Usage:", cpu_usage, "%")
        if cpu_usage > CPU_THRESHOLD and active_backend == "local":
            print("[CPU Monitor] High CPU usage detected. Triggering scale-up...")
            scale_up()
        elif cpu_usage < CPU_DOWNSCALE_THRESHOLD and active_backend == "gcp":
            print("[CPU Monitor] Low CPU usage detected. Triggering scale-down...")
            scale_down()
        time.sleep(1)


def handle_client(client_socket):
    backend_socket = None
    current_backend_ip = BACKEND_IP  # Track the current backend IP

    while True:
        try:
            # Check if the backend IP has changed or the socket is closed
            if backend_socket is None or backend_socket._closed or current_backend_ip != BACKEND_IP:
                # Close existing connection if any
                if backend_socket:
                    backend_socket.close()
                    print(f"[Client Handler] Disconnected from old backend: {current_backend_ip}")

                # Update to the new backend IP and reconnect
                current_backend_ip = BACKEND_IP
                print(f"[Client Handler] Connecting to new backend at {current_backend_ip}:{BACKEND_PORT}...")
                backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                backend_socket.connect((current_backend_ip, BACKEND_PORT))
                print("[Client Handler] Connected to backend server.")

            # Receive data from the client
            data = client_socket.recv(1024)
            if not data:
                print("[Client Handler] Client disconnected.")
                break

            # Send data to the backend and get the response
            backend_socket.sendall(data)
            response = backend_socket.recv(1024)
            client_socket.sendall(response)

        except Exception as e:
            print(f"[Client Handler] Backend server not available or connection lost: {str(e)}")
            # Close the backend socket to trigger reconnection
            if backend_socket:
                backend_socket.close()
                backend_socket = None
            print("[Client Handler] Waiting 2 seconds before retrying...")
            time.sleep(2)


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("0.0.0.0", FRONTEND_PORT))
server.listen(5)
print("[Frontend] Server listening on port", FRONTEND_PORT)

cpu_monitor_thread = threading.Thread(target=monitor_cpu)
cpu_monitor_thread.daemon = True
cpu_monitor_thread.start()

while True:
    client_sock, addr = server.accept()
    print("[Frontend] Accepted connection from", addr)
    client_thread = threading.Thread(target=handle_client, args=(client_sock,))
    client_thread.start()



