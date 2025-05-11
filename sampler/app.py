# sampler/app.py  — resilient OpenCV sampler
import os, time, cv2, kafka, logging, signal, sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

RTSP_URL      = os.getenv("CAM_RTSP")                  # e.g. rtsp://mediamtx:8554/iphone
KAFKA_BROKER  = os.getenv("KAFKA_BROKER", "redpanda:9092")
TOPIC         = os.getenv("TOPIC", "frames")
JPEG_QUALITY  = int(os.getenv("JPEG_Q", "80"))
TARGET_FPS    = float(os.getenv("TARGET_FPS", "5"))    # send 5 frames / s

producer = kafka.KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda b: b,                      # raw bytes to Kafka
)

running = True
def _graceful(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, _graceful)
signal.signal(signal.SIGINT,  _graceful)

sleep_between_retries = 5          # seconds
next_send_time        = 0.0

while running:
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logging.warning("Camera unavailable, retrying in %s s …", sleep_between_retries)
        cap.release()
        time.sleep(sleep_between_retries)
        continue

    logging.info("✅ Stream opened → %s", RTSP_URL)

    while running and cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            logging.warning("Lost connection - will reopen after %s s", sleep_between_retries)
            break                                             # exits inner loop → reopen
        now = time.time()
        if now < next_send_time:                              # FPS throttle
            continue
        next_send_time = now + 1.0 / TARGET_FPS
        _, jpg = cv2.imencode(".jpg", frame,
                              [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        logging.info("sending frame")
        producer.send(TOPIC, jpg.tobytes())

    cap.release()
    time.sleep(sleep_between_retries)

logging.info("Shutting down sampler")
producer.flush()
producer.close()

