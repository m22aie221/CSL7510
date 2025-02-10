import requests
import sys

def send_message(server_ip, port=5000):
    message = {"message": "Hi Server"}
    print(f"Sending: {message['message']}")
    try:
        response = requests.post(
            f'http://{server_ip}:{port}/hello',
            json=message
        )
        data = response.json()
        print(f"Server reponse Rcvd: {data['message']}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_ip>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    send_message(server_ip)