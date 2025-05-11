import os, io, json, time, kafka, PIL.Image as Image
from ultralytics import YOLO

broker   = os.getenv("KAFKA_BROKER")
in_t     = os.getenv("IN_TOPIC",  "frames")
out_t    = os.getenv("OUT_TOPIC", "detections")
model    = YOLO("yolov8n.pt")     # small demo model

consumer = kafka.KafkaConsumer(in_t, bootstrap_servers=broker,
                               value_deserializer=lambda x: x)
producer = kafka.KafkaProducer(bootstrap_servers=broker,
                               value_serializer=lambda d: json.dumps(d).encode())

for msg in consumer:
    img = Image.open(io.BytesIO(msg.value)).convert("RGB")
    results = model.predict(img, imgsz=640, conf=0.3)
    detections = [{
        "cls": model.names[int(b.boxes.cls[i])],
        "conf": float(b.boxes.conf[i]),
        "xyxy": [float(c) for c in b.boxes.xyxy[i]]
    } for i, b in enumerate(results)]
    out = {"ts": time.time(), "cam": "cam1", "dets": detections}
    producer.send(out_t, out)

