import socket

BACKEND_PORT = 9000
connected = False  # Track connection status

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", BACKEND_PORT))
server.listen(1)  # Accept only one connection at a time
print("Backend server listening on port", BACKEND_PORT)

while True:
    if not connected:  # Accept connection only if not already connected
        client_socket, addr = server.accept()
        connected = True
        print("Accepted connection from", addr)

        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    print("Client disconnected.")
                    break
                print("Backend received:", data.decode())
                response = f"Hi Client"
                client_socket.sendall(response.encode())
                print("Backend sent:", response)
        except Exception as e:
            print("Error while communicating:", str(e))
        finally:
            client_socket.close()
            connected = False  # Reset connection status after closing
            print("Connection closed")
