import os
import time
import psutil
import paramiko

# GCP Configuration
GCP_INSTANCE_NAME = "autoscale-server"
GCP_ZONE = "us-central1-a"
GCP_USERNAME = "your-username"
GCP_IP = None
GCP_KEY_FILE = "/path/to/gcp-key.pem"

# Local Server Script
LOCAL_SERVER_SCRIPT = "server.py"
REMOTE_SERVER_SCRIPT = "/home/{}/server.py".format(GCP_USERNAME)

# Client Config
CLIENT_CONFIG_FILE = "client.py"

def check_cpu_usage():
    return psutil.cpu_percent(interval=5)

def create_gcp_instance():
    os.system(f"gcloud compute instances create {GCP_INSTANCE_NAME} "
              f"--machine-type=e2-micro --image-family=ubuntu-2004-lts "
              f"--image-project=ubuntu-os-cloud --zone={GCP_ZONE} --tags=http-server")

def get_gcp_ip():
    global GCP_IP
    GCP_IP = os.popen(f"gcloud compute instances list --filter='name={GCP_INSTANCE_NAME}' "
                      f"--format='get(networkInterfaces[0].accessConfigs[0].natIP)'").read().strip()
    return GCP_IP

def transfer_files():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(GCP_IP, username=GCP_USERNAME, key_filename=GCP_KEY_FILE)

    sftp = ssh.open_sftp()
    sftp.put(LOCAL_SERVER_SCRIPT, REMOTE_SERVER_SCRIPT)
    sftp.close()

    ssh.exec_command(f"nohup python3 {REMOTE_SERVER_SCRIPT} > server.log 2>&1 &")
    ssh.close()

def update_client():
    with open(CLIENT_CONFIG_FILE, "r") as file:
        client_data = file.read()

    new_client_data = client_data.replace("SERVER_IP = \"127.0.0.1\"", f"SERVER_IP = \"{GCP_IP}\"")

    with open(CLIENT_CONFIG_FILE, "w") as file:
        file.write(new_client_data)

    print(f"Client updated to use new GCP Server IP: {GCP_IP}")

while True:
    cpu_usage = check_cpu_usage()
    print(f"CPU Usage: {cpu_usage}%")

    if cpu_usage > 75:
        print("High CPU detected! Migrating server to GCP...")

        create_gcp_instance()
        time.sleep(30)  # Wait for GCP instance to boot

        GCP_IP = get_gcp_ip()
        print(f"GCP Instance IP: {GCP_IP}")

        transfer_files()
        update_client()
        print("Migration complete. Server is now running on GCP.")
        break

    time.sleep(5)
