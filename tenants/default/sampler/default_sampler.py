"""
Default Sampling Implementation

This module implements the sampling interface with sensible defaults.
"""
import os
import cv2
import numpy as np
from typing import Dict, Any, Optional
import time
import sys

# Add the project root to the Python path
sys.path.append("/app")
from interfaces.sampling_interface import SamplingInterface


class DefaultSampler(SamplingInterface):
    """Default implementation of the SamplingInterface."""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the sampler with configuration values.
        
        Args:
            config: Dictionary containing configuration values
        """
        self.target_fps = float(config.get("TARGET_FPS", 5))
        self.jpeg_quality = int(config.get("JPEG_Q", 80))
        self.base_topic = config.get("BASE_TOPIC", "frames")
        self.last_sample_time = {}  # Track last sample time per camera
    
    def should_sample(self, frame: np.ndarray, metadata: Dict[str, Any]) -> bool:
        """Sample frames at a fixed rate based on TARGET_FPS.
        
        Args:
            frame: OpenCV image frame
            metadata: Dictionary with frame metadata including camera_id and timestamp
            
        Returns:
            bool: True if the frame should be sampled based on FPS control
        """
        camera_id = metadata.get("camera_id", "default")
        now = time.time()
        
        # Initialize last sample time if not present
        if camera_id not in self.last_sample_time:
            self.last_sample_time[camera_id] = 0
        
        # Check if enough time has passed since the last sampled frame
        if now >= self.last_sample_time[camera_id] + (1.0 / self.target_fps):
            self.last_sample_time[camera_id] = now
            return True
        
        return False
    
    def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Optional[np.ndarray]:
        """Pass through the frame without modifications.
        
        Args:
            frame: OpenCV image frame
            metadata: Dictionary with frame metadata
            
        Returns:
            np.ndarray: The original frame
        """
        # In the default implementation, we don't modify the frame
        return frame
    
    def get_topic(self, camera_id: str) -> str:
        """Get the Kafka topic name for a camera.
        
        Args:
            camera_id: Identifier for the camera source
            
        Returns:
            str: Topic name in format "{base_topic}.{camera_id}"
        """
        return f"{self.base_topic}.{camera_id}"