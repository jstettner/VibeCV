"""
Sampling Interface for Tenant-Specific Frame Selection

This module defines the interface that tenant-specific sampling logic must implement.
The interface allows for custom frame selection based on tenant-specific criteria.
"""
from abc import ABC, abstractmethod
import cv2
import numpy as np
from typing import Dict, Any, Optional


class SamplingInterface(ABC):
    """Abstract base class defining the interface for tenant-specific sampling logic."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the sampler with tenant-specific configuration.
        
        Args:
            config: Dictionary containing tenant-specific configuration
        """
        pass
    
    @abstractmethod
    def should_sample(self, frame: np.ndarray, metadata: Dict[str, Any]) -> bool:
        """Determine if the current frame should be sampled based on tenant-specific logic.
        
        Args:
            frame: OpenCV image frame (BGR format)
            metadata: Dictionary containing frame metadata (timestamp, camera_id, etc.)
            
        Returns:
            bool: True if the frame should be sampled, False otherwise
        """
        pass
    
    @abstractmethod
    def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Optional[np.ndarray]:
        """Optional pre-processing of the frame before publishing to Kafka.
        
        This method allows tenants to modify the frame before it's sent for inference.
        Return None to skip this frame entirely.
        
        Args:
            frame: OpenCV image frame (BGR format)
            metadata: Dictionary containing frame metadata
            
        Returns:
            Optional[np.ndarray]: Processed frame or None if frame should be skipped
        """
        pass
    
    @abstractmethod
    def get_topic(self, camera_id: str) -> str:
        """Get the Kafka topic name for a specific camera.
        
        This allows tenants to define custom topic naming schemes.
        
        Args:
            camera_id: Identifier for the camera source
            
        Returns:
            str: Kafka topic name to publish frames to
        """
        pass