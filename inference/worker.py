"""
inference/worker.py
────────────────────────────────────────────────────────────────
A no-dependency demo “inference” node that uses only OpenCV.

Pipeline
--------
Kafka (frames topic, JPEG bytes)  ─►  OpenCV (background model)
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

# ───────────────────────── Config via env vars ──────────────────────────
KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "redpanda:9092")
IN_TOPIC       = os.getenv("IN_TOPIC", "frames")
OUT_TOPIC      = os.getenv("OUT_TOPIC", "detections")
FRAME_PATH     = Path(os.getenv("FRAME_PATH", "/frames/cam1.jpg"))
MIN_AREA_PX    = int(os.getenv("MIN_AREA_PX", "1500"))      # ignore blobs < this
FRAME_RATE_OUT = float(os.getenv("TARGET_FPS", "5"))        # jpeg write cap
JPEG_QUALITY   = int(os.getenv("JPEG_Q", "80"))

# ───────────────────────── Kafka setup ──────────────────────────────────
consumer = kafka.KafkaConsumer(
    IN_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda b: b,  # keep raw JPEG bytes
    auto_offset_reset="latest",
    group_id="inference-opencv",
    enable_auto_commit=True,
)

producer = kafka.KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda d: json.dumps(d).encode(),
)

# ───────────────────────── OpenCV helpers ───────────────────────────────
bg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)

def jpeg_to_array(buf: bytes) -> np.ndarray:
    """Decode JPEG bytes → BGR ndarray."""
    img_arr = np.frombuffer(buf, dtype=np.uint8)
    return cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

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
signal.signal(signal.SIGTERM, _exit)
signal.signal(signal.SIGINT,  _exit)

# ───────────────────────── Main loop ────────────────────────────────────
print("[inference] 🏃‍♂️  Starting loop…", flush=True)
next_preview_time = 0.0

for msg in consumer:
    if not running:
        break

    frame = jpeg_to_array(msg.value)
    if frame is None:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    fgmask = bg.apply(gray)

    # Basic morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=2)

    contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA_PX:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        detections.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area)})
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Publish detections JSON (one message per frame)
    try:
        producer.send(OUT_TOPIC, {"ts": time.time(), "count": len(detections), "boxes": detections})
    except KafkaError as e:
        print(f"[inference] KafkaError: {e}", file=sys.stderr)

    # Throttle preview writes so we don't spam the side-car
    now = time.time()
    if now >= next_preview_time:
        write_preview(frame)
        next_preview_time = now + 1.0 / FRAME_RATE_OUT

print("[inference] ✋ Shutting down…")
producer.flush()
producer.close()
consumer.close()

