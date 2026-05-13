"""
Video Analyzer Service
─────────────────────
Accepts a local video file path, extracts frames using OpenCV,
runs YOLOv8 on each frame, and returns all detections + tracked persons.
"""
import os
from dataclasses import dataclass

import cv2

from app.services.person_tracker import PersonRegistry

WEAPON_CLASSES = {"knife", "scissors", "gun", "pistol", "rifle", "sword"}
WEAPON_CONF_THRESHOLD = 0.20   # Lower threshold so held/partial knives are caught
DEFAULT_CONF_THRESHOLD = 0.35


@dataclass
class FrameDetection:
    frame_number: int
    timestamp_seconds: float
    objects: list[dict]
    screenshot_path: str | None = None


@dataclass
class VideoAnalysisResult:
    video_path: str
    total_frames_processed: int
    duration_seconds: float
    fps_processed: int
    detections: list[FrameDetection]
    unique_classes: list[str]
    summary: dict
    person_registry: PersonRegistry | None = None   # ← NEW


# ─────────────────────────────────────────────────────────────────────────────
# Singleton YOLO model loader
# ─────────────────────────────────────────────────────────────────────────────
_yolo_model = None


def get_yolo_model(model_path: str = "yolov8s.pt"):
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        print(f"⏳ Loading YOLOv8 model: {model_path}")
        _yolo_model = YOLO(model_path)
        print("✅ YOLOv8 model ready")
    return _yolo_model


# ─────────────────────────────────────────────────────────────────────────────
# Main analysis function
# ─────────────────────────────────────────────────────────────────────────────
def analyze_video(
    video_path: str,
    sample_fps: int = 2,
    confidence_threshold: float = DEFAULT_CONF_THRESHOLD,
    save_annotated_frames: bool = False,
    output_dir: str | None = None,
) -> VideoAnalysisResult:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / native_fps

    # Fix for browser WebM files that report absurdly high FPS
    actual_fps = native_fps if 0 < native_fps <= 120 else 30.0
    frame_interval = max(1, int(actual_fps / sample_fps))

    model = get_yolo_model()
    detections: list[FrameDetection] = []
    class_counts: dict[str, int] = {}
    frame_idx = 0
    analyzed = 0

    # ── Per-analysis person registry ─────────────────────────────────────────
    registry = PersonRegistry()

    print(f"📹 Analyzing: {video_path}")
    print(f"   Duration: {duration_seconds:.1f}s | Reported FPS: {native_fps:.1f} | Using: {actual_fps:.1f} | Sample: {sample_fps}fps")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp = frame_idx / actual_fps
            h, w = frame.shape[:2]

            # Run YOLO at the lowest threshold to catch everything, then filter per-class
            results = model.predict(frame, conf=WEAPON_CONF_THRESHOLD, verbose=False)

            frame_objects = []
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = result.names[cls_id]
                    conf = float(box.conf[0])

                    # Apply per-class minimum confidence
                    min_conf = WEAPON_CONF_THRESHOLD if cls_name in WEAPON_CLASSES else confidence_threshold
                    if conf < min_conf:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    bbox_pixels = [int(x1), int(y1), int(x2), int(y2)]

                    obj = {
                        "class": cls_name,
                        "confidence": round(conf, 3),
                        "bbox": [
                            round(x1 / w, 4), round(y1 / h, 4),
                            round(x2 / w, 4), round(y2 / h, 4),
                        ],
                        "bbox_pixels": bbox_pixels,
                        # Re-ID fields (filled in below for persons)
                        "person_id": None,
                        "tag_color": None,
                        "threat_level": None,
                        "sighting_count": None,
                    }

                    frame_objects.append(obj)
                    class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

            if frame_objects:
                import uuid
                filename = f"screenshot_{uuid.uuid4().hex[:8]}_{frame_idx}.jpg"
                filepath = os.path.join("app", "uploads", "screenshots", filename)

                # ── Re-ID: identify every person in this frame ─────────────
                for obj in frame_objects:
                    if obj["class"] == "person":
                        person = registry.identify_person(
                            frame=frame,
                            bbox_pixels=obj["bbox_pixels"],
                            frame_number=frame_idx,
                            timestamp=timestamp,
                            screenshot_path=filename,
                        )
                        if person:
                            obj["person_id"] = person.person_id
                            obj["tag_color"] = person.tag_color
                            obj["threat_level"] = person.threat_level
                            obj["sighting_count"] = person.sighting_count
                            
                            # Draw bounding box for tracked person
                            x1, y1, x2, y2 = obj["bbox_pixels"]
                            # OpenCV uses BGR
                            color = (50, 205, 50) # emerald
                            if person.tag_color == "red":
                                color = (0, 0, 255) # red
                            elif person.tag_color == "yellow":
                                color = (0, 255, 255) # yellow
                                
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            label = f"{person.person_id} ({person.threat_level})"
                            cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # Save the frame after all bounding boxes are drawn
                cv2.imwrite(filepath, frame)

                detections.append(FrameDetection(
                    frame_number=frame_idx,
                    timestamp_seconds=round(timestamp, 3),
                    objects=frame_objects,
                    screenshot_path=filename
                ))

            analyzed += 1

        frame_idx += 1

    cap.release()
    repeat_count = len(registry.get_repeat_persons())
    alert_count = len(registry.get_alert_persons())
    print(f"✅ Done. Analyzed {analyzed} frames, found detections in {len(detections)} frames.")
    print(f"👥 Re-ID: {registry._counter} unique persons | {repeat_count} repeat | {alert_count} frequent (alert)")

    return VideoAnalysisResult(
        video_path=video_path,
        total_frames_processed=analyzed,
        duration_seconds=round(duration_seconds, 2),
        fps_processed=sample_fps,
        detections=detections,
        unique_classes=sorted(class_counts.keys()),
        summary=class_counts,
        person_registry=registry,
    )
