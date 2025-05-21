# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Argus is a computer vision system for processing video streams with person detection capabilities. The system operates as a set of connected Docker containers, each handling a specific part of the video processing pipeline.

## Build & Run Commands

### Starting the System

```bash
# Start all containers in the background
docker compose up -d

# Start specific containers
docker compose up -d mediamtx redpanda sampler inference preview

# View container logs
docker compose logs -f [container_name]

# Restart a container
docker compose restart [container_name]
```

### Streaming Video

1. From an iPhone:
   - Download Streamcast Pro from the App Store
   - Get your LAN IP address: `ipconfig getifaddr en0`
   - Configure Streamcast Pro with URL: `rtmp://<your-ip>:1935/live/iphone`
   - Start streaming

2. Using the demo camera (included):
   - This is automatically started with `docker compose up`
   - Uses a looping video clip for testing

### Viewing Output

- Preview server with bounding boxes: http://localhost:8000/stream
- MediaMTX web interface: http://localhost:8888/

## System Architecture

The Argus system works as a pipeline of connected components:

1. **Video Ingestion** (`mediamtx`)
   - RTSP/RTMP streaming server based on MediaMTX
   - Accepts streams from demo_cam or external sources like iPhones
   - Exposes ports 8554 (RTSP), 1935 (RTMP), 8888 (HTTP API)

2. **Message Bus** (`redpanda`)
   - Kafka-compatible message broker for stream processing
   - Used for frame and detection data exchange between components
   - Runs on port 9092

3. **Frame Sampling** (`sampler`)
   - Captures frames from video streams at controlled intervals
   - Publishes JPEG-encoded frames to Kafka `frames` topic
   - Configurable framerate via `TARGET_FPS` environment variable

4. **Inference** (`inference`)
   - Subscribes to the `frames` topic
   - Performs object detection using YOLOv8 model to detect people
   - Draws bounding boxes around detected people
   - Publishes detection data to Kafka `detections` topic
   - Writes annotated frames to shared volume for preview

5. **Preview Server** (`preview`)
   - Serves processed frames with detection visualizations
   - Simple FastAPI-based MJPEG streaming server
   - Available at http://localhost:8000/stream

6. **Demo Camera** (`demo_cam`)
   - Loops a sample video for testing without external cameras
   - Streams via RTSP to MediaMTX

## Data Flow

```
External camera/iPhone → MediaMTX → Sampler → Kafka (frames topic) → 
Inference → Kafka (detections topic) + shared volume → Preview Server → Browser
```

## Configuration

Most components are configured via environment variables in `docker-compose.yml`:

- **Sampler**:
  - `CAM_RTSP`: RTSP URL to capture from
  - `TARGET_FPS`: Frame sampling rate
  - `JPEG_Q`: JPEG encoding quality

- **Inference**:
  - `CONFIDENCE_THRESHOLD`: Minimum confidence for person detection (default: 0.4)
  - `MODEL_NAME`: YOLOv8 model to use (default: yolov8n.pt)

## Development Notes

- The system is designed to be modular - components communicate via Kafka topics
- Shared frames are stored in a RAM-based tmpfs volume for speed
- GPU acceleration can be enabled by uncommenting NVIDIA runtime settings in the inference service
- Future components include MinIO (object storage) and TimescaleDB (time-series data)