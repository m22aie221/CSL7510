import requests
import time

SERVER_IP = "127.0.0.1"  # Initially points to local VM
PORT = 5000

def send_message(server_ip):
    message = {"message": "Hi Server"}
    try:
        response = requests.post(f'http://{server_ip}:{PORT}/hello', json=message, timeout=3)
        print(f"Response from {server_ip}: {response.json()['message']}")
    except requests.exceptions.RequestException:
        print(f"Server {server_ip} is unreachable!")

while True:
    send_message(SERVER_IP)
    time.sleep(5)  # Send message every 5 seconds
