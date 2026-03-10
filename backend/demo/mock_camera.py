"""Mock camera for DEMO_MODE.

Generates synthetic student detection data — no real camera or OpenCV capture
needed.  The ``MockCamera`` class is consumed by ``VisionAgent`` when
``config.DEMO_MODE`` is ``True``.

Detection results include random attention fluctuations so the Dashboard
shows realistic, changing data during an expo demo.
"""

import random
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Default mock student roster (matched with mock_students.py)
# ---------------------------------------------------------------------------

_MOCK_STUDENT_IDS = [
    "demo_s001",
    "demo_s002",
    "demo_s003",
    "demo_s004",
    "demo_s005",
]


class MockCamera:
    """Generates synthetic per-student detection results.

    Instead of returning raw video frames (which would require OpenCV /
    numpy), ``MockCamera`` returns a list of detection dicts that
    ``VisionAgent._demo_loop`` can pass directly to
    ``_update_attention``.

    Each *detection* is a ``dict`` with keys:

    * ``student_id`` – one of the demo student IDs
    * ``attention_score`` – random float in ``[0.0, 1.0]``
    * ``present`` – whether the student appears in this "frame"

    Usage::

        cam = MockCamera()
        cam.start()
        detections = cam.read()  # list of detection dicts
        cam.stop()
    """

    def __init__(self, student_ids: Optional[List[str]] = None) -> None:
        """Initialise with an optional list of student IDs to simulate.

        Args:
            student_ids: IDs of students to cycle through.  Defaults to the
                five demo students defined in ``mock_students.py``.
        """
        self._student_ids: List[str] = student_ids or list(_MOCK_STUDENT_IDS)
        self._is_running: bool = False
        # Per-student baseline attention so changes feel gradual
        self._baselines: Dict[str, float] = {
            sid: random.uniform(0.5, 0.9) for sid in self._student_ids
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark camera as running (no real resources acquired)."""
        self._is_running = True

    def stop(self) -> None:
        """Mark camera as stopped."""
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Return ``True`` if the mock camera is active."""
        return self._is_running

    # ------------------------------------------------------------------
    # Frame generation
    # ------------------------------------------------------------------

    def read(self) -> List[Dict]:
        """Return a list of synthetic detection dicts for one "frame".

        Returns:
            List of dicts, each containing ``student_id``,
            ``attention_score`` (float 0–1), and ``present`` (bool).
        """
        detections: List[Dict] = []

        for sid in self._student_ids:
            # 90 % of the time the student is "visible"
            present = random.random() < 0.9

            if present:
                baseline = self._baselines[sid]
                # Gradually drift the baseline
                drift = random.uniform(-0.05, 0.05)
                baseline = max(0.2, min(1.0, baseline + drift))
                self._baselines[sid] = baseline

                # Add per-frame noise around the baseline
                noise = random.uniform(-0.1, 0.1)
                score = max(0.0, min(1.0, baseline + noise))
            else:
                score = 0.0

            detections.append(
                {
                    "student_id": sid,
                    "attention_score": score,
                    "present": present,
                }
            )

        return detections

    # ------------------------------------------------------------------
    # Context manager support (mirrors cv2.VideoCapture usage pattern)
    # ------------------------------------------------------------------

    def __enter__(self) -> "MockCamera":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
