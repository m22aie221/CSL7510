from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/hello', methods=['POST'])
def hello():
    data = request.get_json()
    client_ip = request.remote_addr
    print(f"Client message Rcvd: {data['message']}")
    return jsonify({'message': 'Hello Client'})

if __name__ == '__main__':
    print("Hello Server running on port 5000...")
    app.run(host='0.0.0.0', port=5000)