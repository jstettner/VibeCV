FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libjpeg-turbo-progs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir opencv-python-headless kafka-python pillow ultralytics

COPY worker.py /worker.py
CMD ["python", "/worker.py"]

