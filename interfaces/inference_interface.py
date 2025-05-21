"""
Inference Interface for Tenant-Specific Detection Logic

This module defines the interface that tenant-specific inference logic must implement.
The interface allows for custom object detection and event detection across multiple frames.
"""
from abc import ABC, abstractmethod
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class InferenceInterface(ABC):
    """Abstract base class defining the interface for tenant-specific inference logic."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the inference engine with tenant-specific configuration.
        
        Args:
            config: Dictionary containing tenant-specific configuration
        """
        pass
    
    @abstractmethod
    def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Process a frame and perform object detection.
        
        Args:
            frame: OpenCV image frame (BGR format)
            metadata: Dictionary containing frame metadata (timestamp, camera_id, etc.)
            
        Returns:
            Tuple containing:
              - np.ndarray: Annotated frame with bounding boxes or other visualizations
              - Dict[str, Any]: Detection results (objects, confidence scores, etc.)
        """
        pass
    
    @abstractmethod
    def buffer_frame(self, frame: np.ndarray, metadata: Dict[str, Any], detections: Dict[str, Any]) -> None:
        """Add a frame to the buffer for multi-frame analysis.
        
        This method allows tenants to maintain a history of frames for temporal analysis.
        
        Args:
            frame: OpenCV image frame (BGR format)
            metadata: Dictionary containing frame metadata
            detections: Detection results from process_frame
        """
        pass
    
    @abstractmethod
    def detect_events(self) -> List[Dict[str, Any]]:
        """Analyze buffered frames to detect complex events.
        
        This method should be called periodically to analyze the frame buffer
        and detect events that span multiple frames (e.g., motion patterns).
        
        Returns:
            List[Dict[str, Any]]: List of detected events with relevant metadata
        """
        pass
    
    @abstractmethod
    def get_clips(self) -> List[Dict[str, Any]]:
        """Generate video clips for significant events.
        
        Returns:
            List[Dict[str, Any]]: List of clip metadata with paths to temporary clip files
        """
        pass
    
    @abstractmethod
    def get_thumbnails(self) -> List[Dict[str, Any]]:
        """Generate thumbnails for significant events or objects.
        
        Returns:
            List[Dict[str, Any]]: List of thumbnail metadata with paths to temporary image files
        """
        pass
    
    @abstractmethod
    def get_output_topics(self) -> Dict[str, str]:
        """Get the Kafka topic names for publishing different types of data.
        
        Returns:
            Dict[str, str]: Mapping of data types to topic names
                (e.g., {'detections': 'detections', 'events': 'events'})
        """
        pass