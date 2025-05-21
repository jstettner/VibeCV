# sampler/Dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg && \
    pip install kafka-python opencv-python-headless numpy

# Create app directory structure
WORKDIR /app

# Copy interface definitions
COPY interfaces /app/interfaces/

# Copy the main app
COPY ./sampler/app.py /app/app.py

# The tenant-specific implementation will be mounted at runtime
# in /app/tenant/sampler/

ENTRYPOINT ["python", "/app/app.py"]