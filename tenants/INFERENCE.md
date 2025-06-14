# Inference Interface Guide

This document explains how to create custom inference logic for the Ambral computer vision system. The inference engine is responsible for processing frames, detecting objects or events, and producing results that can be stored or acted upon.

## Interface

Your custom inference engine must implement the `InferenceInterface` abstract base class defined in `/interfaces/inference_interface.py`. This interface requires the following methods:

```python
def initialize(self, config: Dict[str, Any]) -> None:
    """Initialize the inference engine with tenant-specific configuration."""
    pass

def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Process a frame and perform object detection."""
    pass

def buffer_frame(self, frame: np.ndarray, metadata: Dict[str, Any], detections: Dict[str, Any]) -> None:
    """Add a frame to the buffer for multi-frame analysis."""
    pass

def detect_events(self) -> List[Dict[str, Any]]:
    """Analyze buffered frames to detect complex events."""
    pass

def get_clips(self) -> List[Dict[str, Any]]:
    """Generate video clips for significant events."""
    pass

def get_thumbnails(self) -> List[Dict[str, Any]]:
    """Generate thumbnails for significant events or objects."""
    pass

def get_output_topics(self) -> Dict[str, str]:
    """Get the Kafka topic names for publishing different types of data."""
    pass
```

## Implementation Guidelines

### 1. File Structure

Create a Python file in your tenant's directory:

```
tenants/
└── your_tenant_id/
    └── inference/
        └── your_inference.py
```

### 2. Importing the Interface

Make sure to import the base interface:

```python
import sys
sys.path.append("/app")
from interfaces.inference_interface import InferenceInterface
```

### 3. Class Implementation

Implement a class that inherits from the `InferenceInterface`:

```python
class YourCustomInference(InferenceInterface):
    # Implement required methods here
```

### 4. Method Implementation Details

#### `initialize(self, config)`

This method is called once when the inference engine starts. Use it to:

- Load models
- Set up configuration parameters
- Initialize buffers or state variables
- Prepare resources

The `config` parameter is a dictionary containing all environment variables.

#### `process_frame(self, frame, metadata)`

This is the main method for processing each sampled frame:

- Run object detection or other computer vision tasks
- Annotate the frame with results (e.g., bounding boxes)
- Return both the annotated frame and the detection results

The method should return a tuple containing:

1. The annotated frame (np.ndarray)
2. A dictionary of detection results, typically including:
   - `ts`: Timestamp
   - `count`: Number of detections
   - `boxes`: List of bounding boxes and details for each detection
   - `camera_id`: The source camera

#### `buffer_frame(self, frame, metadata, detections)`

This method stores frames, metadata, and detection results for multi-frame analysis:

- Add the frame to a memory buffer (e.g., a deque with a fixed size)
- Store the associated metadata and detections
- Manage buffer size to avoid memory issues

#### `detect_events(self)`

This method analyzes the buffered frames to detect events that span multiple frames:

- Events are patterns or changes across time (e.g., a person entering a zone)
- Return a list of detected events, each as a dictionary
- Called periodically (by default, once per second)

Example event types:

- Person entering/exiting an area
- Object left behind
- Unusual motion patterns
- Counting behaviors over time

#### `get_clips(self)`

This method creates short video clips for significant events:

- Generate clips from the buffered frames
- Return metadata about the clips (e.g., file path, associated event)
- Clips can later be uploaded to object storage

In a future version, this will integrate with MinIO for clip storage.

#### `get_thumbnails(self)`

Similar to `get_clips()`, but for still images:

- Extract key frames or regions of interest
- Return metadata about the thumbnails
- Used for preview or archiving

In a future version, this will integrate with MinIO for thumbnail storage.

#### `get_output_topics(self)`

This method defines the Kafka topics where different types of data will be published:

- Return a dictionary mapping data types to topic names
- Common outputs include: `detections`, `events`, `metrics`

## Configuration

Your custom inference engine will have access to all environment variables set in the Docker container. The key variables you may want to use are:

- `TENANT_ID`: Your tenant identifier
- `CONFIDENCE_THRESHOLD`: Minimum confidence score for detections
- `MODEL_NAME`: Name of the model to use
- `EVENT_CHECK_INTERVAL`: How often to check for events (seconds)

You can add custom environment variables in the docker-compose file.

## Example

Here's a simplified example of a custom inference engine that detects cars in addition to people:

```python
class CarAndPersonDetector(InferenceInterface):
    def initialize(self, config):
        # Load YOLOv8 model
        self.model_name = config.get("MODEL_NAME", "yolov8n.pt")
        self.confidence_threshold = float(config.get("CONFIDENCE_THRESHOLD", 0.4))
        self.model = YOLO(self.model_name)

        # Initialize buffers
        self.max_buffer_size = int(config.get("BUFFER_SIZE", 30))
        self.frame_buffer = deque(maxlen=self.max_buffer_size)
        self.detection_buffer = deque(maxlen=self.max_buffer_size)
        self.metadata_buffer = deque(maxlen=self.max_buffer_size)

        # Set output topics
        self.out_topics = {
            "detections": config.get("DETECTIONS_TOPIC", "detections"),
            "events": config.get("EVENTS_TOPIC", "events"),
            "car_counts": config.get("CAR_COUNTS_TOPIC", "car_counts")
        }

    def process_frame(self, frame, metadata):
        # Copy frame for annotation
        annotated_frame = frame.copy()

        # Run YOLOv8 inference
        results = self.model.predict(frame, verbose=False, conf=self.confidence_threshold)

        # Process detections - now include both people and cars
        detections = []
        car_count = 0
        person_count = 0

        if results and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]

                if label in ["person", "car"]:
                    if label == "car":
                        color = (0, 0, 255)  # Red for cars
                        car_count += 1
                    else:
                        color = (0, 255, 0)  # Green for people
                        person_count += 1

                    detections.append({
                        "x": x1, "y": y1,
                        "w": x2 - x1, "h": y2 - y1,
                        "confidence": conf,
                        "class": label
                    })

                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    label_text = f"{label}: {conf:.2f}"
                    cv2.putText(annotated_frame, label_text, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Add counts to the frame
        count_text = f"People: {person_count}, Cars: {car_count}"
        cv2.putText(annotated_frame, count_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Prepare detection results
        detection_results = {
            "ts": time.time(),
            "count": len(detections),
            "people_count": person_count,
            "car_count": car_count,
            "boxes": detections,
            "camera_id": metadata.get("camera_id", "default")
        }

        return annotated_frame, detection_results

    # ... implement other methods ...
```

## Deploying Your Custom Inference

To use your custom inference engine:

1. Set the following environment variables in your docker-compose configuration:

   ```yaml
   environment:
     TENANT_INFERENCE_PATH: /app/tenant/inference/your_inference.py
     TENANT_INFERENCE_CLASS: YourCustomInference
   ```

2. Make sure your tenant directory is mounted:
   ```yaml
   volumes:
     - ./tenants/your_tenant_id/inference:/app/tenant/inference:ro
   ```

## Performance Considerations

- Consider using GPU acceleration for deep learning models
- Use efficient buffer management to avoid memory leaks
- For time-critical applications, optimize frame processing
- Consider the trade-off between detection quality and speed
- When using custom models, ensure they're optimized for your hardware
