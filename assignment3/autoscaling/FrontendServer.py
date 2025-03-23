# server.py
import socket
import threading
import time

BACKEND_IP = "127.0.0.1"
BACKEND_PORT = 9000
FRONTEND_PORT = 8000


def handle_client(client_socket):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as backend_socket:
                print("Attempting to connect to backend server...")
                backend_socket.connect((BACKEND_IP, BACKEND_PORT))
                print("Connected to backend server.")

                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    print("Frontend received:", data.decode())
                    backend_socket.sendall(data)
                    response = backend_socket.recv(1024)
                    client_socket.sendall(response)
                    print("Frontend forwarded response:", response.decode())
        except Exception as e:
            print("Backend server not available. Retrying in 2 seconds...")
            time.sleep(2)


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", FRONTEND_PORT))
server.listen(5)
print("Frontend server listening on port", FRONTEND_PORT)

while True:
    client_sock, addr = server.accept()
    print("Accepted connection from", addr)
    client_thread = threading.Thread(target=handle_client, args=(client_sock,))
    client_thread.start()