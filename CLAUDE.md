# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Argus is a computer vision system that uses video streams for object detection. The system captures video frames from cameras (like iPhones streaming via RTMP), processes those frames with object detection models, and outputs the detected objects.

## Architecture

The system consists of several containerized components:

1. **MediaMTX** - Media server that handles RTMP streams from cameras
2. **Redpanda** - Kafka-compatible message broker
3. **Sampler** - Python service that extracts frames from video streams and publishes to Kafka
4. **Inference** - Python service using OpenCV to perform object detection on frames

Data flows:
- Camera → MediaMTX → Sampler → Redpanda (`frames` topic) → Inference → Redpanda (`detections` topic)

## Development Commands

### Starting the Application

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f sampler
```

### Streaming From an iPhone

1. Find your LAN IP address:
```bash
ipconfig getifaddr en0
```

2. Configure a streaming app like Streamcast Pro with:
```
rtmp://<your-ip-address>:1935/live/iphone
```

### Stopping the Application

```bash
docker compose down
```

### Rebuilding Container Images

```bash
# Rebuild a specific service
docker compose build sampler

# Rebuild and restart
docker compose up -d --build
```

## Environment Variables

Key configuration is controlled via environment variables in docker-compose.yml:

- **Sampler**:
  - `KAFKA_BROKER`: Kafka broker address
  - `TOPIC`: Output Kafka topic
  - `CAM_RTSP`: RTSP URL for camera stream
  - `TARGET_FPS`: Target frames per second to process (default: 5)
  - `JPEG_QUALITY`: JPEG quality for frame compression (default: 80)

- **Inference**:
  - `KAFKA_BROKER`: Kafka broker address
  - `IN_TOPIC`: Input Kafka topic (default: "frames")
  - `OUT_TOPIC`: Output Kafka topic (default: "detections")
