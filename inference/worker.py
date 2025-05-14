"""
inference/worker.py
────────────────────────────────────────────────────────────────
A demo “inference” node that uses OpenCV and YOLOv8.

Pipeline
--------
Kafka (frames topic, JPEG bytes)  ─►  YOLOv8 (object detection)
                                   ─►  bounding-box drawing
                                   ├─►  Kafka (detections topic, JSON)
                                   └─►  /frames/cam1.jpg  (for preview sidecar)
"""

import io
import json
import os
import signal
import sys
import time
from pathlib import Path

import cv2
import kafka
import numpy as np
from kafka.errors import KafkaError
from ultralytics import YOLO

# ───────────────────────── Config via env vars ──────────────────────────
KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "redpanda:9092")
IN_TOPIC       = os.getenv("IN_TOPIC", "frames")
OUT_TOPIC      = os.getenv("OUT_TOPIC", "detections")
FRAME_PATH     = Path(os.getenv("FRAME_PATH", "/frames/cam1.jpg"))
# MIN_AREA_PX    = int(os.getenv("MIN_AREA_PX", "1500"))      # No longer used with YOLO
FRAME_RATE_OUT = float(os.getenv("TARGET_FPS", "5"))        # jpeg write cap
JPEG_QUALITY   = int(os.getenv("JPEG_Q", "80"))
MODEL_NAME     = os.getenv("MODEL_NAME", "yolov8n.pt") # Nano model, good balance of speed/accuracy
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4")) # Min detection confidence

# ───────────────────────── Kafka setup ──────────────────────────────────
consumer = kafka.KafkaConsumer(
    IN_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda b: b,  # keep raw JPEG bytes
    auto_offset_reset="latest",
    group_id="inference-yolo", # Changed group_id to reflect new model
    enable_auto_commit=True,
)

producer = kafka.KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda d: json.dumps(d).encode(),
)

# ───────────────────────── YOLO Model ───────────────────────────────
# Load a pre-trained YOLOv8 model
try:
    model = YOLO(MODEL_NAME)
    print(f"✅ YOLO model '{MODEL_NAME}' loaded successfully.", flush=True)
except Exception as e:
    print(f"❌ Error loading YOLO model '{MODEL_NAME}': {e}", file=sys.stderr, flush=True)
    sys.exit(1)


def jpeg_to_array(buf: bytes) -> np.ndarray | None:
    """Decode JPEG bytes → BGR ndarray."""
    try:
        img_arr = np.frombuffer(buf, dtype=np.uint8)
        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if frame is None:
            print("[inference] Frame decoding failed.", file=sys.stderr)
        return frame
    except Exception as e:
        print(f"[inference] Error decoding JPEG: {e}", file=sys.stderr)
        return None

def write_preview(frame: np.ndarray) -> None:
    """Save annotated frame to shared volume for the preview side-car."""
    ok, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if ok:
        FRAME_PATH.parent.mkdir(parents=True, exist_ok=True)
        FRAME_PATH.write_bytes(enc.tobytes())

# ───────────────────────── Graceful shutdown ────────────────────────────
running = True
def _exit(_sig, _frm):
    global running
    running = False
    print("[inference] Signal received, initiating shutdown...", flush=True)
signal.signal(signal.SIGTERM, _exit)
signal.signal(signal.SIGINT,  _exit)

# ───────────────────────── Main loop ────────────────────────────────────
print("🏃 Starting YOLO inference loop…", flush=True)
next_preview_time = 0.0

for msg in consumer:
    if not running:
        break

    frame = jpeg_to_array(msg.value)
    if frame is None:
        continue

    # Perform object detection
    results = model.predict(frame, verbose=False, conf=CONFIDENCE_THRESHOLD) # verbose=False to reduce console spam

    detections = []
    if results and results[0].boxes:
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = model.names[cls_id]

            if label == "person": # Filter for 'person' detections
                detections.append({
                    "x": x1, "y": y1,
                    "w": x2 - x1, "h": y2 - y1,
                    "confidence": conf,
                    "class": label
                })
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Add label
                label_text = f"{label}: {conf:.2f}"
                cv2.putText(frame, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Publish detections JSON (one message per frame)
    if detections: # Only send if there are relevant (person) detections
        try:
            producer.send(OUT_TOPIC, {"ts": time.time(), "count": len(detections), "boxes": detections})
        except KafkaError as e:
            print(f"[inference] KafkaError sending detections: {e}", file=sys.stderr)

    # Throttle preview writes
    now = time.time()
    if now >= next_preview_time:
        write_preview(frame)
        next_preview_time = now + 1.0 / FRAME_RATE_OUT

print("[inference] ✋ Shutting down consumer and producer…")
if consumer:
    consumer.close()
    print("[inference] Consumer closed.", flush=True)
if producer:
    producer.flush()
    producer.close()
    print("[inference] Producer flushed and closed.", flush=True)

print("[inference] Shutdown complete.", flush=True)

