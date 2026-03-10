"""Attention monitoring agent for the AI Autonomous Lecturer.

Provides two capabilities:

* **Speech sentiment analysis:** Uses a DistilBERT classifier to determine
  whether a student's transcribed speech indicates confusion, clarity, or
  boredom — helping Gemini decide whether to slow down or speed up.
* **Attention summary aggregation:** Pulls per-student attention scores from
  ``lecture_state`` and returns a structured summary used by the
  ``get_class_status`` MCP tool.

DEMO_MODE (``config.DEMO_MODE == True``):
  Returns mock sentiment / attention data without loading any ML model.
"""

import logging
from typing import Optional

from backend import config
from backend.orchestrator.lecture_state import lecture_state

logger = logging.getLogger(__name__)


class AttentionAgent:
    """Analyses student attention using NLP and aggregated vision scores.

    The DistilBERT pipeline is lazy-loaded on the first call to
    ``analyse_speech_sentiment`` to avoid slow startup times.

    Usage::

        agent = AttentionAgent()
        result = agent.analyse_speech_sentiment("I don't understand this part")
        # → {"sentiment": "negative", "confidence": 0.93, "confused": True}
    """

    def __init__(self) -> None:
        """Initialise the agent (model loading is deferred)."""
        self._classifier = None
        logger.info(
            "AttentionAgent initialised (DEMO_MODE=%s)", config.DEMO_MODE
        )

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_classifier(self) -> None:
        """Lazy-load the DistilBERT sentiment-analysis pipeline."""
        if self._classifier is not None:
            return
        if config.DEMO_MODE:
            return
        try:
            from transformers import pipeline  # type: ignore[import-untyped]

            logger.info("Loading DistilBERT sentiment pipeline…")
            self._classifier = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
            )
            logger.info("DistilBERT sentiment pipeline loaded")
        except Exception:
            logger.exception("AttentionAgent: failed to load DistilBERT pipeline")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse_speech_sentiment(self, text: str) -> dict:
        """Run sentiment analysis on student speech.

        A negative sentiment score is treated as an indicator of confusion or
        disengagement, prompting Gemini to re-explain the current concept.

        Args:
            text: The transcribed student speech to analyse.

        Returns:
            dict with keys:
              * ``sentiment`` — "positive" | "negative"
              * ``confidence`` — float [0.0 – 1.0]
              * ``confused`` — bool (True when negative sentiment is strong)
        """
        if config.DEMO_MODE or not text.strip():
            return {"sentiment": "positive", "confidence": 0.8, "confused": False}

        self._load_classifier()

        if self._classifier is None:
            logger.warning("AttentionAgent: classifier unavailable — returning neutral")
            return {"sentiment": "positive", "confidence": 0.5, "confused": False}

        try:
            results = self._classifier(text[:512])  # DistilBERT max tokens
            if not results:
                raise ValueError("Empty classifier output")
            result = results[0]
            sentiment: str = result["label"].lower()
            confidence: float = float(result["score"])
            confused = sentiment == "negative" and confidence > 0.7
            logger.debug(
                "AttentionAgent sentiment: %s (%.2f) confused=%s",
                sentiment,
                confidence,
                confused,
            )
            return {"sentiment": sentiment, "confidence": confidence, "confused": confused}
        except Exception:
            logger.exception("AttentionAgent: sentiment analysis error")
            return {"sentiment": "positive", "confidence": 0.5, "confused": False}

    def get_attention_summary(self) -> dict:
        """Aggregate per-student attention data from ``lecture_state``.

        Returns a summary dict intended for use by the ``get_class_status``
        MCP tool, giving Gemini a quick overview of class engagement.

        Returns:
            dict with keys:
              * ``average_attention`` — float [0.0 – 1.0]
              * ``most_distracted`` — student_id string or None
              * ``most_distracted_name`` — student display name or None
              * ``most_distracted_score`` — float or None
              * ``attentive_count`` — int
              * ``distracted_count`` — int
              * ``trend`` — "improving" | "declining" | "stable"
        """
        if config.DEMO_MODE:
            return {
                "average_attention": 0.75,
                "most_distracted": None,
                "most_distracted_name": None,
                "most_distracted_score": None,
                "attentive_count": 3,
                "distracted_count": 1,
                "trend": "stable",
            }

        students = lecture_state.students
        if not students:
            return {
                "average_attention": 1.0,
                "most_distracted": None,
                "most_distracted_name": None,
                "most_distracted_score": None,
                "attentive_count": 0,
                "distracted_count": 0,
                "trend": "stable",
            }

        present = [s for s in students.values() if s.is_present]
        if not present:
            present = list(students.values())

        scores = {s.id: s.attention_score for s in present}
        avg = sum(scores.values()) / len(scores) if scores else 1.0

        most_distracted_id: Optional[str] = None
        most_distracted_score: Optional[float] = None
        if scores:
            most_distracted_id = min(scores, key=lambda k: scores[k])
            most_distracted_score = scores[most_distracted_id]

        distracted_count = sum(1 for sc in scores.values() if sc < 0.3)
        attentive_count = len(present) - distracted_count

        # Simple trend: compare current average with the overall present proportion
        if avg > 0.7:
            trend = "stable"
        elif avg > 0.4:
            trend = "declining"
        else:
            trend = "declining"

        most_distracted_name: Optional[str] = None
        if most_distracted_id and most_distracted_id in students:
            most_distracted_name = students[most_distracted_id].name

        return {
            "average_attention": round(avg, 2),
            "most_distracted": most_distracted_id,
            "most_distracted_name": most_distracted_name,
            "most_distracted_score": (
                round(most_distracted_score, 2) if most_distracted_score is not None else None
            ),
            "attentive_count": attentive_count,
            "distracted_count": distracted_count,
            "trend": trend,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
attention_agent = AttentionAgent()
