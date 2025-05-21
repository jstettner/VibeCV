# sampler/app.py — modular frame sampler using tenant-specific code
import os
import time
import cv2
import kafka
import logging
import signal
import sys
import importlib.util
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Configuration via environment variables
RTSP_URL = os.getenv("CAM_RTSP")                  # e.g. rtsp://mediamtx:8554/iphone
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
CAMERA_ID = os.getenv("CAMERA_ID", os.path.basename(RTSP_URL or "default"))
TENANT_ID = os.getenv("TENANT_ID", "default")
TENANT_MODULE_PATH = os.getenv("TENANT_SAMPLER_PATH", f"/app/tenant/sampler/default_sampler.py")
TENANT_CLASS_NAME = os.getenv("TENANT_SAMPLER_CLASS", "DefaultSampler")

# Load the tenant-specific sampler module
try:
    spec = importlib.util.spec_from_file_location("tenant_sampler", TENANT_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec from {TENANT_MODULE_PATH}")
    
    tenant_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tenant_module)
    
    SamplerClass = getattr(tenant_module, TENANT_CLASS_NAME)
    sampler = SamplerClass()
    
    logging.info(f"✅ Loaded tenant sampler: {TENANT_CLASS_NAME} from {TENANT_MODULE_PATH}")
except Exception as e:
    logging.error(f"❌ Failed to load tenant sampler: {e}")
    sys.exit(1)

# Initialize the Kafka producer
producer = kafka.KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda b: b,  # raw bytes to Kafka
)

# Initialize the tenant-specific sampler
tenant_config = {k: v for k, v in os.environ.items()}  # Pass all environment variables
sampler.initialize(tenant_config)

# Signal handling for graceful shutdown
running = True
def _graceful(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, _graceful)
signal.signal(signal.SIGINT, _graceful)

sleep_between_retries = 5  # seconds

while running:
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logging.warning(f"Camera unavailable, retrying in {sleep_between_retries} s …")
        cap.release()
        time.sleep(sleep_between_retries)
        continue

    logging.info(f"✅ Stream opened → {RTSP_URL}")

    while running and cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            logging.warning(f"Lost connection - will reopen after {sleep_between_retries} s")
            break  # exits inner loop → reopen
        
        # Create metadata for the frame
        metadata = {
            "timestamp": time.time(),
            "camera_id": CAMERA_ID,
            "tenant_id": TENANT_ID,
            "rtsp_url": RTSP_URL
        }
        
        # Let tenant-specific code decide if we should sample this frame
        if sampler.should_sample(frame, metadata):
            # Process the frame through tenant-specific logic
            processed_frame = sampler.process_frame(frame, metadata)
            
            # Skip if the tenant returns None
            if processed_frame is None:
                continue
            
            # Encode as JPEG and send to Kafka
            _, jpg = cv2.imencode(".jpg", processed_frame)
            
            # Get the appropriate topic from tenant logic
            topic = sampler.get_topic(CAMERA_ID)
            
            logging.info(f"Sending frame to topic: {topic}")
            producer.send(topic, jpg.tobytes())

    cap.release()
    time.sleep(sleep_between_retries)

logging.info("Shutting down sampler")
producer.flush()
producer.close()