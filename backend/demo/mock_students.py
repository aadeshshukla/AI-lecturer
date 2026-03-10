"""Demo student seeding for DEMO_MODE.

When ``DEMO_MODE=true`` and no students exist in the database, this module
creates five realistic demo students so a lecture can start immediately
without any manual student registration.

The mock photo paths point to placeholder images under
``data/student_photos/`` — the files do not need to exist for the system to
run; the vision agent bypasses real face recognition in DEMO_MODE.
"""

import logging
import os
from typing import List

from sqlalchemy.orm import Session

from backend.database.students import create_student, get_all_students
from backend.models.student import Student

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo student roster
# ---------------------------------------------------------------------------

DEMO_STUDENTS: List[dict] = [
    {
        "id": "demo_s001",
        "name": "Alice Chen",
        "email": "alice.chen@demo.example",
        "photo_path": "data/student_photos/demo_s001.jpg",
    },
    {
        "id": "demo_s002",
        "name": "Bob Kumar",
        "email": "bob.kumar@demo.example",
        "photo_path": "data/student_photos/demo_s002.jpg",
    },
    {
        "id": "demo_s003",
        "name": "Carol Smith",
        "email": "carol.smith@demo.example",
        "photo_path": "data/student_photos/demo_s003.jpg",
    },
    {
        "id": "demo_s004",
        "name": "David Park",
        "email": "david.park@demo.example",
        "photo_path": "data/student_photos/demo_s004.jpg",
    },
    {
        "id": "demo_s005",
        "name": "Eve Johnson",
        "email": "eve.johnson@demo.example",
        "photo_path": "data/student_photos/demo_s005.jpg",
    },
]


def seed_demo_students(db: Session) -> int:
    """Create demo students if the database is empty.

    This is idempotent — if any students already exist the function does
    nothing and returns 0.

    Args:
        db: Active SQLAlchemy session.

    Returns:
        Number of students created (0 if students already existed).
    """
    existing = get_all_students(db)
    if existing:
        logger.info(
            "seed_demo_students: %d student(s) already exist — skipping seed",
            len(existing),
        )
        return 0

    # Ensure the photos directory exists (actual image files are not required
    # in DEMO_MODE since DeepFace is bypassed).
    os.makedirs("data/student_photos", exist_ok=True)

    created_count = 0
    for spec in DEMO_STUDENTS:
        student = Student(
            id=spec["id"],
            name=spec["name"],
            email=spec["email"],
            photo_path=spec["photo_path"],
        )
        try:
            create_student(db, student)
            created_count += 1
            logger.info(
                "seed_demo_students: created %s (%s)", spec["id"], spec["name"]
            )
        except Exception:
            logger.exception(
                "seed_demo_students: failed to create %s — skipping", spec["id"]
            )

    return created_count
