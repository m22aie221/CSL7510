from flask import Flask, request, jsonify
import socket

app = Flask(__name__)

@app.route('/hello', methods=['POST'])
def hello():
    data = request.get_json()
    client_ip = request.remote_addr
    print(f"Message from {client_ip}: {data['message']}")
    return jsonify({'message': 'Hello from Server!'})

if __name__ == "__main__":
    print(f"Server running on {socket.gethostname()}:5000")
    app.run(host="0.0.0.0", port=5000)
