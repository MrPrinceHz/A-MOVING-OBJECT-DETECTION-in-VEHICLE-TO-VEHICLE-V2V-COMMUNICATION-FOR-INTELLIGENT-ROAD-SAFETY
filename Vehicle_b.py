from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import time
import os

app = Flask(__name__)
vehicle_keys = {}  # Store vehicle_id -> public_key

@app.route('/register', methods=['POST'])
def register_vehicle():
    data = request.get_json()
    vehicle_id = data['vehicle_id']
    public_key_str = data['public_key']

    # Save the key to a file
    key_path = f"{vehicle_id}_public.pem"
    with open(key_path, "w") as f:
        f.write(public_key_str)

    # Load and store the key in memory
    public_key = serialization.load_pem_public_key(
        public_key_str.encode(),
        backend=default_backend()
    )
    vehicle_keys[vehicle_id] = public_key

    print(f"[✔] Registered vehicle: {vehicle_id} with public key.")
    return jsonify({"status": "registered"}), 200

@app.route('/receive', methods=['POST'])
def receive_data():
    data = request.get_json()
    vehicle_id = data["vehicle_id"]
    signature = bytes.fromhex(data["signature"])
    detection_data = data["data"]

    if vehicle_id not in vehicle_keys:
        return jsonify({"error": "vehicle not registered"}), 400

    public_key = vehicle_keys[vehicle_id]
    try:
        public_key.verify(
            signature,
            str(detection_data).encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print(f"\n[RECEIVED] from {vehicle_id} @ {detection_data['timestamp']}")
        print(f"Detections: {detection_data['detections']}")
        return jsonify({"status": "valid", "received": True})
    except Exception as e:
        print(f"[!] Invalid signature from {vehicle_id}")
        return jsonify({"status": "invalid", "received": False}), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)