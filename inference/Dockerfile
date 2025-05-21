# inference/Dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libjpeg-turbo-progs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir opencv-python-headless kafka-python pillow ultralytics

# Create app directory structure
WORKDIR /app

# Copy interface definitions
COPY interfaces /app/interfaces/

# Copy the worker script
COPY ./inference/worker.py /app/worker.py

# The tenant-specific implementation will be mounted at runtime
# in /app/tenant/inference/

CMD ["python", "/app/worker.py"]