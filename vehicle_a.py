import cv2
import time
import requests
from ultralytics import YOLO
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# Load YOLO model
model = YOLO("/home/prince-hazarika/Downloads/yolov12_best.pt")  # Update path

# Generate key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# Serialize public key to PEM
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

# Send public key to Vehicle B
receiver_url = "http://192.168.86.204:5000"  # Replace with actual IP
vehicle_id = "VehicleA"

registration_payload = {
    "vehicle_id": vehicle_id,
    "public_key": public_pem
}

r = requests.post(f"{receiver_url}/register", json=registration_payload)
print("[🔐] Public key sent for registration:", r.json())

# Start camera and detect
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)[0]
    detections = []
    for box, conf, cls in zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls):
        label = results.names[int(cls)]
        detections.append({
            "label": label,
            "confidence": round(float(conf), 2),
            "bbox": box.int().tolist()
        })

    payload = {
        "vehicle_id": vehicle_id,
        "data": {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "detections": detections
        }
    }

    signature = private_key.sign(
        str(payload["data"]).encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    payload["signature"] = signature.hex()

    try:
        res = requests.post(f"{receiver_url}/receive", json=payload, timeout=1)
        print(f"[→] Sent detections: {res.json()}")
    except Exception as e:
        print(f"[x] Failed to send: {e}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()

