"""
Default Inference Implementation

This module implements the inference interface with person detection using YOLOv8.
"""
import os
import cv2
import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple, Deque
from collections import deque
import sys
from ultralytics import YOLO

# Add the project root to the Python path
sys.path.append("/app")
from interfaces.inference_interface import InferenceInterface


class DefaultInference(InferenceInterface):
    """Default implementation of the InferenceInterface using YOLOv8 for person detection."""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the inference engine with configuration values.
        
        Args:
            config: Dictionary containing configuration values
        """
        # Load model configuration
        self.model_name = config.get("MODEL_NAME", "yolov8n.pt")
        self.confidence_threshold = float(config.get("CONFIDENCE_THRESHOLD", 0.4))
        self.max_buffer_size = int(config.get("BUFFER_SIZE", 30))
        self.out_topics = {
            "detections": config.get("DETECTIONS_TOPIC", "detections"),
            "events": config.get("EVENTS_TOPIC", "events")
        }
        
        # Initialize the YOLOv8 model
        try:
            self.model = YOLO(self.model_name)
            print(f"✅ YOLO model '{self.model_name}' loaded successfully.", flush=True)
        except Exception as e:
            print(f"❌ Error loading YOLO model '{self.model_name}': {e}", file=sys.stderr, flush=True)
            raise
        
        # Initialize frame buffer (for multi-frame analysis)
        self.frame_buffer = deque(maxlen=self.max_buffer_size)
        self.detection_buffer = deque(maxlen=self.max_buffer_size)
        self.metadata_buffer = deque(maxlen=self.max_buffer_size)
        
    def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Process a frame and perform person detection using YOLOv8.
        
        Args:
            frame: OpenCV image frame (BGR format)
            metadata: Dictionary containing frame metadata
            
        Returns:
            Tuple containing:
              - np.ndarray: Annotated frame with bounding boxes
              - Dict[str, Any]: Detection results
        """
        # Create a copy of the frame for annotation
        annotated_frame = frame.copy()
        
        # Run YOLOv8 inference
        results = self.model.predict(frame, verbose=False, conf=self.confidence_threshold)
        
        detections = []
        if results and results[0].boxes:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                
                if label == "person":  # Filter for 'person' detections
                    detections.append({
                        "x": x1, "y": y1,
                        "w": x2 - x1, "h": y2 - y1,
                        "confidence": conf,
                        "class": label
                    })
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Add label
                    label_text = f"{label}: {conf:.2f}"
                    cv2.putText(annotated_frame, label_text, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Prepare detection results
        detection_results = {
            "ts": time.time(),
            "count": len(detections),
            "boxes": detections,
            "camera_id": metadata.get("camera_id", "default")
        }
        
        return annotated_frame, detection_results
    
    def buffer_frame(self, frame: np.ndarray, metadata: Dict[str, Any], detections: Dict[str, Any]) -> None:
        """Add a frame to the buffer for multi-frame analysis.
        
        Args:
            frame: OpenCV image frame
            metadata: Dictionary containing frame metadata
            detections: Detection results from process_frame
        """
        self.frame_buffer.append(frame)
        self.metadata_buffer.append(metadata)
        self.detection_buffer.append(detections)
    
    def detect_events(self) -> List[Dict[str, Any]]:
        """Analyze buffered frames to detect events (e.g., person entering/exiting).
        
        The default implementation detects when people enter or exit the frame.
        
        Returns:
            List[Dict[str, Any]]: List of detected events
        """
        events = []
        
        # Need at least 2 frames to detect changes
        if len(self.detection_buffer) < 2:
            return events
        
        # Compare current and previous frame
        current = self.detection_buffer[-1]
        previous = self.detection_buffer[-2]
        
        current_count = current.get("count", 0)
        previous_count = previous.get("count", 0)
        
        camera_id = current.get("camera_id", "default")
        timestamp = current.get("ts", time.time())
        
        # Person entered
        if current_count > previous_count:
            events.append({
                "type": "person_entered",
                "camera_id": camera_id,
                "timestamp": timestamp,
                "current_count": current_count,
                "previous_count": previous_count
            })
        
        # Person exited
        elif current_count < previous_count:
            events.append({
                "type": "person_exited",
                "camera_id": camera_id,
                "timestamp": timestamp,
                "current_count": current_count,
                "previous_count": previous_count
            })
        
        return events
    
    def get_clips(self) -> List[Dict[str, Any]]:
        """Generate video clips for significant events.
        
        The default implementation doesn't generate clips, but demonstrates the interface.
        In a real implementation, this would save clips to a temporary location for MinIO upload.
        
        Returns:
            List[Dict[str, Any]]: Empty list in default implementation
        """
        # Not implemented in default version - would require video encoder setup
        return []
    
    def get_thumbnails(self) -> List[Dict[str, Any]]:
        """Generate thumbnails for detected persons.
        
        In a real implementation, this would extract person images and save to temp files.
        
        Returns:
            List[Dict[str, Any]]: Empty list in default implementation
        """
        # Not implemented in default version
        return []
    
    def get_output_topics(self) -> Dict[str, str]:
        """Get the Kafka topic names for publishing different types of data.
        
        Returns:
            Dict[str, str]: Mapping of data types to topic names
        """
        return self.out_topics