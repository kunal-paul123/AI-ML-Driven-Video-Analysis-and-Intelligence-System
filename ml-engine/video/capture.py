"""
Video capture abstraction supporting:
- Local file paths (.mp4, .avi, .mkv)
- RTSP streams (rtsp://...)
- Webcam (index integer)
- HTTP MJPEG streams
"""
import cv2
import time
from dataclasses import dataclass
from typing import Generator


@dataclass
class Frame:
    """A single decoded video frame."""
    data: object          # numpy ndarray (BGR)
    frame_number: int
    timestamp: float      # epoch seconds
    source_id: str
    width: int
    height: int


class VideoCapture:
    """
    Unified video capture class for all input types.

    Usage:
        cap = VideoCapture(source="rtsp://192.168.1.1/stream", source_id="cam-01")
        cap.open()
        for frame in cap.read_frames(fps=5):
            process(frame)
        cap.close()
    """

    def __init__(self, source: str | int, source_id: str = "unknown"):
        self.source = source
        self.source_id = source_id
        self._cap: cv2.VideoCapture | None = None
        self.frame_number = 0

    def open(self) -> bool:
        """Open the video source. Returns True on success."""
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            print(f"❌ Failed to open video source: {self.source}")
            return False
        print(f"✅ Video source opened: {self.source}")
        return True

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def native_fps(self) -> float:
        if self._cap:
            return self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        return 30.0

    def read_frame(self) -> Frame | None:
        """Read a single frame. Returns None on end-of-stream or error."""
        if not self.is_open:
            return None
        ret, frame_data = self._cap.read()
        if not ret:
            return None
        self.frame_number += 1
        h, w = frame_data.shape[:2]
        return Frame(
            data=frame_data,
            frame_number=self.frame_number,
            timestamp=time.time(),
            source_id=self.source_id,
            width=w,
            height=h,
        )

    def read_frames(self, fps: int = 5) -> Generator[Frame, None, None]:
        """
        Generator that yields frames at approximately the given FPS.
        Skips frames from faster sources to meet target FPS.
        """
        interval = 1.0 / fps
        last_yield = 0.0

        while self.is_open:
            frame = self.read_frame()
            if frame is None:
                break
            now = time.time()
            if now - last_yield >= interval:
                last_yield = now
                yield frame

    def close(self):
        """Release the video source."""
        if self._cap:
            self._cap.release()
            self._cap = None
        print(f"🛑 Video source closed: {self.source}")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()
