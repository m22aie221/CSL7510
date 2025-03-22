import sys
import socket
import time

if len(sys.argv) != 3:
    print("Usage: python client.py <server_ip> <port>")
    sys.exit(1)

server_ip = sys.argv[1]
port = int(sys.argv[2])
message_count = 0

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_ip, port))
        print("Connected to server.")
        while True:
            message_count += 1
            message = f"Hello Server {message_count}"
            client_socket.sendall(message.encode())
            print("Client sent:", message)
            response = client_socket.recv(1024).decode()
            print("Server responded:", response)
            time.sleep(1)
except Exception as e:
    print("Error:", e)