"""Redaction service for RapidAPI facade.

Provides unified redaction functionality with support for
different modes (mask/placeholder) and entity filtering.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.pii_detector import DetectedEntity, get_detector


@dataclass
class RedactedEntity:
    """Entity with redaction information and score."""

    entity_type: str
    start: int
    end: int
    score: float


# Placeholder templates for each entity type
PLACEHOLDER_TEMPLATES = {
    "PERSON": "<PERSON>",
    "EMAIL": "<EMAIL>",
    "PHONE": "<PHONE>",
    "CARD": "<CARD>",
    "SENSITIVE_WORD": "<SENSITIVE_WORD>",
}

# Default mask token
MASK_TOKEN = "***"

# Scores for different detection methods
REGEX_SCORE = 1.0  # Regex matches are deterministic
NER_DEFAULT_SCORE = 0.85  # Default score for NER entities


def filter_entities(
    entities: list[DetectedEntity], allowed_types: list[str] | None = None
) -> list[DetectedEntity]:
    """Filter entities by allowed types.

    Args:
        entities: List of detected entities
        allowed_types: List of entity types to keep. If None, keep all.

    Returns:
        Filtered list of entities
    """
    if allowed_types is None:
        return entities

    allowed_set = set(allowed_types)
    return [e for e in entities if e.type in allowed_set]


def get_entity_score(entity: DetectedEntity) -> float:
    """Get confidence score for an entity.

    Args:
        entity: Detected entity

    Returns:
        Confidence score (0.0 to 1.0)
    """
    # Regex-based detections (EMAIL, PHONE, CARD) get perfect score
    if entity.type in ("EMAIL", "PHONE", "CARD"):
        return REGEX_SCORE

    # NER-based detections (PERSON) get a default score
    # In the future, this could be enhanced to use actual NER scores
    return NER_DEFAULT_SCORE


def apply_redaction(
    text: str, entities: Sequence[DetectedEntity], mode: str
) -> tuple[str, list[RedactedEntity]]:
    """Apply redaction to text based on mode.

    Args:
        text: Original text
        entities: List of detected entities to redact
        mode: "mask" for *** or "placeholder" for <TYPE>

    Returns:
        Tuple of (redacted_text, list of RedactedEntity with scores)
    """
    if not entities:
        return text, []

    # Sort entities by start position descending (right to left replacement)
    sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

    result = text
    redacted_items = []

    for entity in sorted_entities:
        # Determine replacement based on mode
        if mode == "placeholder":
            replacement = PLACEHOLDER_TEMPLATES.get(entity.type, f"<{entity.type}>")
        else:  # mode == "mask"
            replacement = MASK_TOKEN

        # Replace in text
        result = result[: entity.start] + replacement + result[entity.end :]

        # Record redacted entity with score
        redacted_items.append(
            RedactedEntity(
                entity_type=entity.type,
                start=entity.start,
                end=entity.end,
                score=get_entity_score(entity),
            )
        )

    # Reverse to get items in original order (by start position)
    redacted_items.reverse()

    return result, redacted_items


def redact_text(
    text: str, language: str = "en", entities_filter: list[str] | None = None, mode: str = "mask"
) -> tuple[str, list[RedactedEntity]]:
    """Perform full redaction pipeline.

    Args:
        text: Text to redact
        language: Language code for NER
        entities_filter: List of entity types to redact (None = all)
        mode: "mask" or "placeholder"

    Returns:
        Tuple of (redacted_text, list of RedactedEntity)
    """
    # Detect PII using existing detector
    detector = get_detector()
    detected = detector.detect(text, language)

    # Filter by requested entity types
    filtered = filter_entities(detected, entities_filter)

    # Apply redaction
    return apply_redaction(text, filtered, mode)
