"""
inference/worker.py — Modular inference using tenant-specific code
────────────────────────────────────────────────────────────────
A modular inference node that loads tenant-specific inference logic.

Pipeline
--------
Kafka (frames topic, JPEG bytes)  ─►  Tenant-specific inference
                                  ├─►  Kafka (detections topic, JSON)
                                  ├─►  Kafka (events topic, JSON)
                                  └─►  /frames/{camera_id}.jpg  (for preview)
"""

import io
import json
import os
import signal
import sys
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, List

import cv2
import kafka
import numpy as np
from kafka.errors import KafkaError

# ───────────────────────── Config via env vars ──────────────────────────
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
IN_TOPIC = os.getenv("IN_TOPIC", "frames.default")
FRAME_PATH_TEMPLATE = os.getenv("FRAME_PATH_TEMPLATE", "/frames/{camera_id}.jpg")
TENANT_ID = os.getenv("TENANT_ID", "default")
TENANT_MODULE_PATH = os.getenv("TENANT_INFERENCE_PATH", "/app/tenant/inference/default_inference.py")
TENANT_CLASS_NAME = os.getenv("TENANT_INFERENCE_CLASS", "DefaultInference")

# ───────────────────────── Load tenant-specific inference ──────────────────────────
try:
    spec = importlib.util.spec_from_file_location("tenant_inference", TENANT_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec from {TENANT_MODULE_PATH}")
    
    tenant_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tenant_module)
    
    InferenceClass = getattr(tenant_module, TENANT_CLASS_NAME)
    inference_engine = InferenceClass()
    
    print(f"✅ Loaded tenant inference: {TENANT_CLASS_NAME} from {TENANT_MODULE_PATH}", flush=True)
except Exception as e:
    print(f"❌ Failed to load tenant inference: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

# ───────────────────────── Initialize tenant inference ──────────────────────────
tenant_config = {k: v for k, v in os.environ.items()}  # Pass all environment variables
inference_engine.initialize(tenant_config)

# ───────────────────────── Kafka setup ──────────────────────────────────
consumer = kafka.KafkaConsumer(
    IN_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda b: b,  # keep raw JPEG bytes
    auto_offset_reset="latest",
    group_id=f"inference-{TENANT_ID}", 
    enable_auto_commit=True,
)

# Get output topics from tenant-specific logic
out_topics = inference_engine.get_output_topics()

producer = kafka.KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda d: json.dumps(d).encode(),
)

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

def write_preview(frame: np.ndarray, camera_id: str) -> None:
    """Save annotated frame to shared volume for the preview side-car."""
    frame_path = Path(FRAME_PATH_TEMPLATE.format(camera_id=camera_id))
    ok, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ok:
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_bytes(enc.tobytes())

# ───────────────────────── Event processing timer ──────────────────────────
last_event_check = time.time()
EVENT_CHECK_INTERVAL = float(os.getenv("EVENT_CHECK_INTERVAL", "1.0"))  # seconds

# ───────────────────────── Graceful shutdown ────────────────────────────
running = True
def _exit(_sig, _frm):
    global running
    running = False
    print("[inference] Signal received, initiating shutdown...", flush=True)
signal.signal(signal.SIGTERM, _exit)
signal.signal(signal.SIGINT,  _exit)

# ───────────────────────── Main loop ────────────────────────────────────
print("🏃 Starting inference loop…", flush=True)

for msg in consumer:
    if not running:
        break

    # Extract metadata from the message
    # In a real system, this would come from Kafka message metadata
    # For this prototype, we'll parse from the topic name
    topic_parts = msg.topic.split('.')
    camera_id = topic_parts[-1] if len(topic_parts) > 1 else "default"
    
    metadata = {
        "timestamp": time.time(),
        "camera_id": camera_id,
        "tenant_id": TENANT_ID,
        "topic": msg.topic
    }

    # Decode the JPEG frame
    frame = jpeg_to_array(msg.value)
    if frame is None:
        continue

    # Process the frame through tenant-specific logic
    try:
        annotated_frame, detections = inference_engine.process_frame(frame, metadata)
        
        # Add the frame to the buffer for event detection
        inference_engine.buffer_frame(frame, metadata, detections)
        
        # Send detection results to Kafka
        if detections["count"] > 0 and "detections" in out_topics:
            try:
                producer.send(out_topics["detections"], detections)
            except KafkaError as e:
                print(f"[inference] KafkaError sending detections: {e}", file=sys.stderr)
        
        # Write the annotated frame for preview
        write_preview(annotated_frame, camera_id)
        
        # Periodically check for events
        now = time.time()
        if now - last_event_check >= EVENT_CHECK_INTERVAL:
            last_event_check = now
            
            # Detect events across buffered frames
            events = inference_engine.detect_events()
            
            # Send events to Kafka
            if events and "events" in out_topics:
                for event in events:
                    try:
                        producer.send(out_topics["events"], event)
                    except KafkaError as e:
                        print(f"[inference] KafkaError sending event: {e}", file=sys.stderr)
            
            # Get and process any clips or thumbnails
            # In a real system, these would be uploaded to MinIO
            # For now, we just log them
            clips = inference_engine.get_clips()
            thumbnails = inference_engine.get_thumbnails()
            
            if clips:
                print(f"[inference] Generated {len(clips)} clips", flush=True)
            
            if thumbnails:
                print(f"[inference] Generated {len(thumbnails)} thumbnails", flush=True)
                
    except Exception as e:
        print(f"[inference] Error processing frame: {e}", file=sys.stderr)

print("[inference] ✋ Shutting down consumer and producer…")
if consumer:
    consumer.close()
    print("[inference] Consumer closed.", flush=True)
if producer:
    producer.flush()
    producer.close()
    print("[inference] Producer flushed and closed.", flush=True)

print("[inference] Shutdown complete.", flush=True)