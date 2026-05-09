"""
YOLOv8 Object Detector
Wraps Ultralytics YOLO with a clean inference interface.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class DetectionResult:
    """Represents a single object detected in a frame."""
    object_class: str
    confidence: float
    bbox: list[float]          # [x1, y1, x2, y2] normalized 0-1
    track_id: int | None = None
    extra: dict = field(default_factory=dict)


class YOLODetector:
    """
    Real-time object detector using YOLOv8.
    
    Usage:
        detector = YOLODetector(model_path="weights/yolov8n.pt")
        results = detector.detect(frame)  # frame is a numpy BGR image
    """

    # Security-relevant classes to prioritize
    TARGET_CLASSES = {
        "person", "backpack", "handbag", "suitcase",
        "knife", "scissors", "car", "truck", "motorcycle",
    }

    def __init__(
        self,
        model_path: str = "weights/yolov8n.pt",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "cpu",  # Use "cuda" if GPU available
    ):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None

    def load(self):
        """Lazy-load the YOLO model (call once before first inference)."""
        from ultralytics import YOLO
        self.model = YOLO(str(self.model_path))
        self.model.to(self.device)
        print(f"✅ YOLOv8 model loaded from {self.model_path} on {self.device}")
        return self

    def detect(self, frame: np.ndarray) -> list[DetectionResult]:
        """
        Run inference on a single BGR frame.
        Returns a list of DetectionResult objects.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call .load() first.")

        h, w = frame.shape[:2]
        results = self.model.predict(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])

                # Normalize bbox to 0-1
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = [x1 / w, y1 / h, x2 / w, y2 / h]

                detections.append(DetectionResult(
                    object_class=cls_name,
                    confidence=conf,
                    bbox=bbox,
                ))

        return detections

    def detect_and_draw(self, frame: np.ndarray) -> tuple[np.ndarray, list[DetectionResult]]:
        """Run detection and return both annotated frame and detection list."""
        import cv2
        detections = self.detect(frame)
        h, w = frame.shape[:2]
        annotated = frame.copy()

        for det in detections:
            x1 = int(det.bbox[0] * w)
            y1 = int(det.bbox[1] * h)
            x2 = int(det.bbox[2] * w)
            y2 = int(det.bbox[3] * h)

            color = (0, 255, 0) if det.object_class == "person" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{det.object_class} {det.confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return annotated, detections
