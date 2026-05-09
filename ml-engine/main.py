"""
ML Engine Entry Point
Processes video from a source and posts detections to the FastAPI backend.

Usage:
    python main.py --source rtsp://192.168.1.1/stream --camera-id <uuid> --fps 5
    python main.py --source ./test_video.mp4 --camera-id <uuid>
"""
import argparse
import time
import httpx
from datetime import datetime, timezone

from video.capture import VideoCapture
from detectors.yolo_detector import YOLODetector


API_BASE_URL = "http://localhost:8000/api/v1"


def post_detection(camera_id: str, detection, frame):
    """POST a single detection event to the FastAPI backend."""
    payload = {
        "camera_id": camera_id,
        "object_class": detection.object_class,
        "confidence": detection.confidence,
        "bbox": detection.bbox,
        "frame_number": frame.frame_number,
        "frame_width": frame.width,
        "frame_height": frame.height,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        response = httpx.post(f"{API_BASE_URL}/detections/", json=payload, timeout=2.0)
        return response.status_code == 201
    except Exception as e:
        print(f"⚠️  Failed to post detection: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="VideoAI ML Engine")
    parser.add_argument("--source", required=True, help="Video source: file path or RTSP URL")
    parser.add_argument("--camera-id", required=True, help="Camera UUID from the backend")
    parser.add_argument("--fps", type=int, default=5, help="Frame extraction FPS (default: 5)")
    parser.add_argument("--model", default="weights/yolov8n.pt", help="YOLO model path")
    parser.add_argument("--confidence", type=float, default=0.5, help="Detection confidence threshold")
    parser.add_argument("--no-post", action="store_true", help="Run without posting to backend (local test)")
    args = parser.parse_args()

    print(f"🚀 Starting ML Engine")
    print(f"   Source:    {args.source}")
    print(f"   Camera ID: {args.camera_id}")
    print(f"   FPS:       {args.fps}")
    print(f"   Model:     {args.model}")

    detector = YOLODetector(
        model_path=args.model,
        confidence_threshold=args.confidence,
    ).load()

    with VideoCapture(source=args.source, source_id=args.camera_id) as cap:
        if not cap.is_open:
            print("❌ Could not open video source. Exiting.")
            return

        frame_count = 0
        detection_count = 0

        for frame in cap.read_frames(fps=args.fps):
            detections = detector.detect(frame.data)
            frame_count += 1

            for det in detections:
                detection_count += 1
                print(
                    f"[Frame {frame.frame_number}] "
                    f"{det.object_class} ({det.confidence:.2f}) "
                    f"bbox={[round(b, 3) for b in det.bbox]}"
                )
                if not args.no_post:
                    post_detection(args.camera_id, det, frame)

            if frame_count % 50 == 0:
                print(f"📊 Processed {frame_count} frames, {detection_count} total detections")


if __name__ == "__main__":
    main()
