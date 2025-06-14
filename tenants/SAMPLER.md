# Sampler Interface Guide

This document explains how to create custom sampling logic for the Ambral computer vision system. The sampler is responsible for deciding which frames from a video stream should be processed by the inference engine.

## Interface

Your custom sampler must implement the `SamplingInterface` abstract base class defined in `/interfaces/sampling_interface.py`. This interface requires the following methods:

```python
def initialize(self, config: Dict[str, Any]) -> None:
    """Initialize the sampler with tenant-specific configuration."""
    pass

def should_sample(self, frame: np.ndarray, metadata: Dict[str, Any]) -> bool:
    """Determine if the current frame should be sampled."""
    pass

def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Optional[np.ndarray]:
    """Optional pre-processing of the frame before publishing to Kafka."""
    pass

def get_topic(self, camera_id: str) -> str:
    """Get the Kafka topic name for a specific camera."""
    pass
```

## Implementation Guidelines

### 1. File Structure

Create a Python file in your tenant's directory:

```
tenants/
└── your_tenant_id/
    └── sampler/
        └── your_sampler.py
```

### 2. Importing the Interface

Make sure to import the base interface:

```python
import sys
sys.path.append("/app")
from interfaces.sampling_interface import SamplingInterface
```

### 3. Class Implementation

Implement a class that inherits from the `SamplingInterface`:

```python
class YourCustomSampler(SamplingInterface):
    # Implement required methods here
```

### 4. Method Implementation Details

#### `initialize(self, config)`

This method is called once when the sampler starts. Use it to:

- Set up configuration parameters
- Initialize any state variables
- Prepare resources

The `config` parameter is a dictionary containing all environment variables.

#### `should_sample(self, frame, metadata)`

This method determines whether a frame should be processed further:

- Return `True` to sample the frame
- Return `False` to skip the frame

Common sampling strategies include:

- Time-based sampling (e.g., 1 frame per second)
- Motion-based sampling (detect changes between frames)
- Quality-based sampling (skip blurry/dark frames)
- Object-based pre-filtering (basic detection to determine if detailed analysis is needed)

The `metadata` parameter contains:

- `timestamp`: When the frame was captured
- `camera_id`: Identifier for the camera source
- `tenant_id`: Your tenant ID
- `rtsp_url`: The stream URL

#### `process_frame(self, frame, metadata)`

This optional method lets you modify frames before they're sent for inference:

- Return the processed frame to continue
- Return `None` to skip this frame entirely

Common pre-processing includes:

- Resizing the frame
- Converting color spaces
- Applying filters or enhancements
- Cropping to regions of interest
- Adding timestamp or metadata overlays

#### `get_topic(self, camera_id)`

This method defines the Kafka topic where frames will be published:

- The default implementation uses the format: `frames.{camera_id}`
- You can customize this based on your needs (e.g., separating by frame type)

## Configuration

Your custom sampler will have access to all environment variables set in the Docker container. The key variables you may want to use are:

- `CAMERA_ID`: Identifier for the camera stream
- `TENANT_ID`: Your tenant identifier
- `TARGET_FPS`: Target frames per second to sample
- `JPEG_Q`: JPEG quality for frame compression

You can add custom environment variables in the docker-compose file.

## Example

A basic custom sampler that captures one frame every 2 seconds:

```python
class SlowSampler(SamplingInterface):
    def initialize(self, config):
        self.last_sample_time = {}
        self.interval = 2.0  # 2 seconds between samples
        self.base_topic = config.get("BASE_TOPIC", "frames")

    def should_sample(self, frame, metadata):
        camera_id = metadata.get("camera_id", "default")
        now = time.time()

        if camera_id not in self.last_sample_time:
            self.last_sample_time[camera_id] = 0

        if now - self.last_sample_time.get(camera_id, 0) >= self.interval:
            self.last_sample_time[camera_id] = now
            return True

        return False

    def process_frame(self, frame, metadata):
        # No preprocessing, return the frame as is
        return frame

    def get_topic(self, camera_id):
        return f"{self.base_topic}.{camera_id}"
```

## Deploying Your Custom Sampler

To use your custom sampler:

1. Set the following environment variables in your docker-compose configuration:

   ```yaml
   environment:
     TENANT_SAMPLER_PATH: /app/tenant/sampler/your_sampler.py
     TENANT_SAMPLER_CLASS: YourCustomSampler
   ```

2. Make sure your tenant directory is mounted:
   ```yaml
   volumes:
     - ./tenants/your_tenant_id/sampler:/app/tenant/sampler:ro
   ```

## Performance Considerations

- Keep your sampling logic efficient since it runs on every frame
- Consider using OpenCV for fast image processing operations
- For compute-intensive operations, keep them in `process_frame` which only runs on sampled frames
- Use a different sampling strategy per camera if necessary
