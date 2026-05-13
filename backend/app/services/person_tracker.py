"""
Person Re-Identification (Re-ID) Tracker
─────────────────────────────────────────
Tracks individuals across frames using color histogram fingerprinting.
No heavy ML model required — fast, lightweight, works with existing YOLOv8 person crops.

Algorithm:
  1. Crop each detected "person" bounding box from the frame.
  2. Compute a 3-channel (HSV) color histogram as the person's "fingerprint".
  3. Compare against all known person fingerprints using cosine similarity.
  4. If similarity > threshold → same person (update record).
  5. If similarity < threshold → new person (assign new ID).
  6. Persons seen >= REPEAT_THRESHOLD times are tagged as "repeat".
  7. Persons seen >= ALERT_THRESHOLD times trigger a "frequent person" alert.
"""

import cv2
import numpy as np
import time
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.82   # Cosine similarity to consider "same person"
REPEAT_THRESHOLD = 2          # Sightings to mark as "repeat visitor" (yellow)
ALERT_THRESHOLD = 4           # Sightings to trigger red alert
MIN_CROP_SIZE = 30            # Minimum pixel size of crop to bother with


@dataclass
class PersonRecord:
    person_id: str
    fingerprint: np.ndarray      # 96-dim color histogram vector
    sighting_count: int = 1
    first_seen_frame: int = 0
    last_seen_frame: int = 0
    first_seen_timestamp: float = 0.0
    last_seen_timestamp: float = 0.0
    best_screenshot: Optional[str] = None  # Path to clearest sighting
    tag_color: str = "green"               # green → yellow → red
    threat_level: str = "normal"           # normal → repeat → frequent

    def update(self, frame_number: int, timestamp: float, screenshot: Optional[str] = None):
        self.sighting_count += 1
        self.last_seen_frame = frame_number
        self.last_seen_timestamp = timestamp
        if screenshot:
            self.best_screenshot = screenshot
        # Update threat level
        if self.sighting_count >= ALERT_THRESHOLD:
            self.tag_color = "red"
            self.threat_level = "frequent"
        elif self.sighting_count >= REPEAT_THRESHOLD:
            self.tag_color = "yellow"
            self.threat_level = "repeat"


class PersonRegistry:
    """
    Thread-local, per-analysis registry of tracked persons.
    One instance is created per video analysis call — it does NOT persist between
    separate calls (by design, so each new video/webcam clip is tracked fresh).
    
    For cross-session persistence, serialize/deserialize via to_summary().
    """

    def __init__(self):
        self._persons: dict[str, PersonRecord] = {}
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        return f"P{self._counter:03d}"

    @staticmethod
    def _compute_fingerprint(crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Compute a normalized HSV color histogram fingerprint from a person crop.
        Returns a 96-dim vector (32 H-bins × 1 + 32 S-bins × 1 + 32 V-bins × 1).
        """
        if crop is None or crop.size == 0:
            return None
        h, w = crop.shape[:2]
        if h < MIN_CROP_SIZE or w < MIN_CROP_SIZE:
            return None

        # Focus on torso (middle 60% height, avoid head/feet noise)
        y_start = int(h * 0.15)
        y_end = int(h * 0.75)
        torso = crop[y_start:y_end, :]
        if torso.size == 0:
            return None

        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)

        # Compute histograms for each channel
        h_hist = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
        s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
        v_hist = cv2.calcHist([hsv], [2], None, [32], [0, 256]).flatten()

        fingerprint = np.concatenate([h_hist, s_hist, v_hist])

        # L2 normalize
        norm = np.linalg.norm(fingerprint)
        if norm == 0:
            return None
        return fingerprint / norm

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two L2-normalized vectors (just dot product)."""
        return float(np.dot(a, b))

    def identify_person(
        self,
        frame: np.ndarray,
        bbox_pixels: list[int],   # [x1, y1, x2, y2]
        frame_number: int,
        timestamp: float,
        screenshot_path: Optional[str] = None,
    ) -> Optional[PersonRecord]:
        """
        Match a detected person bounding box against the registry.
        Returns the matched (or newly created) PersonRecord.
        """
        x1, y1, x2, y2 = bbox_pixels
        crop = frame[y1:y2, x1:x2]

        fingerprint = self._compute_fingerprint(crop)
        if fingerprint is None:
            return None

        # Find best match among known persons
        best_match_id = None
        best_similarity = 0.0

        for pid, record in self._persons.items():
            sim = self._cosine_similarity(fingerprint, record.fingerprint)
            if sim > best_similarity:
                best_similarity = sim
                best_match_id = pid

        if best_match_id and best_similarity >= SIMILARITY_THRESHOLD:
            # Matched existing person
            record = self._persons[best_match_id]
            # Update fingerprint with exponential moving average for drift robustness
            alpha = 0.3
            updated_fp = alpha * fingerprint + (1 - alpha) * record.fingerprint
            norm = np.linalg.norm(updated_fp)
            record.fingerprint = updated_fp / norm if norm > 0 else updated_fp
            record.update(frame_number, timestamp, screenshot_path)
            return record
        else:
            # New person
            new_id = self._new_id()
            record = PersonRecord(
                person_id=new_id,
                fingerprint=fingerprint,
                sighting_count=1,
                first_seen_frame=frame_number,
                last_seen_frame=frame_number,
                first_seen_timestamp=timestamp,
                last_seen_timestamp=timestamp,
                best_screenshot=screenshot_path,
            )
            self._persons[new_id] = record
            return record

    def get_all_persons(self) -> list[PersonRecord]:
        return list(self._persons.values())

    def get_repeat_persons(self) -> list[PersonRecord]:
        return [p for p in self._persons.values() if p.sighting_count >= REPEAT_THRESHOLD]

    def get_alert_persons(self) -> list[PersonRecord]:
        return [p for p in self._persons.values() if p.sighting_count >= ALERT_THRESHOLD]

    def to_summary(self) -> list[dict]:
        """Serializable summary of all tracked persons."""
        results = []
        for p in sorted(self._persons.values(), key=lambda x: x.sighting_count, reverse=True):
            results.append({
                "person_id": p.person_id,
                "sighting_count": p.sighting_count,
                "tag_color": p.tag_color,
                "threat_level": p.threat_level,
                "first_seen_frame": p.first_seen_frame,
                "last_seen_frame": p.last_seen_frame,
                "first_seen_timestamp": round(p.first_seen_timestamp, 2),
                "last_seen_timestamp": round(p.last_seen_timestamp, 2),
                "best_screenshot": p.best_screenshot,
                "screenshot_url": (
                    f"http://localhost:8000/static/screenshots/{p.best_screenshot}"
                    if p.best_screenshot else None
                ),
            })
        return results
