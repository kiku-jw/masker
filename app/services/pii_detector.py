"""PII Detection service using regex patterns and spaCy NER.

This module provides the PIIDetector class which identifies
personally identifiable information in text.
"""

import contextlib
import re
from dataclasses import dataclass

import spacy
from spacy.language import Language

from app.core.metrics import PII_DETECTED_TOTAL


@dataclass
class DetectedEntity:
    """Represents a detected PII entity."""

    type: str
    value: str
    start: int
    end: int


class PIIDetector:
    """Detects PII in text using regex patterns and spaCy NER.

    Supported entity types:
    - EMAIL: Email addresses
    - PHONE: Phone numbers (international formats)
    - CARD: Credit/debit card numbers
    - PERSON: Person names (via spaCy NER)
    - SENSITIVE_WORD: User-defined sensitive words (via MASKER_SENSITIVE_WORDS env var)
    """

    # Regex patterns for PII detection
    PATTERNS = {
        "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "PHONE": re.compile(
            r"""
            (?:
                # International format: +1, +7, +44, etc.
                \+\d{1,3}[-.\s]?
            )?
            (?:
                # Area code in parentheses: (555)
                \(\d{1,4}\)[-.\s]?
                |
                # Area code without parentheses: 555-
                \d{1,4}[-.\s]
            )?
            # Main number parts
            \d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}
            """,
            re.VERBOSE,
        ),
        "CARD": re.compile(
            r"""
            (?<!\d)  # Not preceded by digit
            (?:
                # Standard 16-digit card with optional separators
                \d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}
                |
                # Amex 15-digit format
                \d{4}[-\s]?\d{6}[-\s]?\d{5}
            )
            (?!\d)  # Not followed by digit
            """,
            re.VERBOSE,
        ),
    }

    # Phone number length constraints to avoid false positives
    MIN_PHONE_LENGTH = 10
    MAX_PHONE_LENGTH = 15  # ITU-T E.164 max is 15 digits

    def __init__(self):
        """Initialize the detector with spaCy models."""
        self._nlp_models: dict[str, Language] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Load spaCy models for supported languages."""
        models_to_load = {
            "en": "en_core_web_sm",
            "ru": "ru_core_news_sm",
        }

        for lang, model_name in models_to_load.items():
            with contextlib.suppress(OSError):
                self._nlp_models[lang] = spacy.load(model_name)

    def _get_nlp(self, language: str) -> Language | None:
        """Get spaCy model for the specified language."""
        return self._nlp_models.get(language)

    def _detect_by_regex(self, text: str) -> list[DetectedEntity]:
        """Detect PII using regex patterns.

        Args:
            text: Input text to scan

        Returns:
            List of detected entities
        """
        entities = []

        for entity_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group()

                # Filter out phone matches that are too short or too long
                if entity_type == "PHONE":
                    digits_only = re.sub(r"\D", "", value)
                    if len(digits_only) < self.MIN_PHONE_LENGTH:
                        continue
                    if len(digits_only) > self.MAX_PHONE_LENGTH:
                        continue

                entities.append(
                    DetectedEntity(
                        type=entity_type, value=value, start=match.start(), end=match.end()
                    )
                )

        return entities

    def _detect_by_ner(self, text: str, language: str) -> list[DetectedEntity]:
        """Detect person names using spaCy NER.

        Args:
            text: Input text to scan
            language: Language code (en, ru)

        Returns:
            List of detected PERSON entities
        """
        nlp = self._get_nlp(language)
        if nlp is None:
            return []

        doc = nlp(text)
        entities = []

        for ent in doc.ents:
            # Map spaCy entity labels to our types
            if ent.label_ in ("PERSON", "PER"):
                entities.append(
                    DetectedEntity(
                        type="PERSON", value=ent.text, start=ent.start_char, end=ent.end_char
                    )
                )

        return entities

    def _detect_sensitive_words(self, text: str) -> list[DetectedEntity]:
        """Detect configured sensitive words using word boundary regex."""
        from app.core.config import settings

        entities = []
        for word in settings.sensitive_word_list:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                entities.append(
                    DetectedEntity(
                        type="SENSITIVE_WORD",
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                )
        return entities

    def _remove_overlaps(self, entities: list[DetectedEntity]) -> list[DetectedEntity]:
        """Remove overlapping entities, preferring regex matches.

        When entities overlap, regex matches (EMAIL, PHONE, CARD) take
        priority over NER matches (PERSON).

        Args:
            entities: List of detected entities

        Returns:
            List with overlapping entities removed
        """
        if not entities:
            return []

        # Sort by start position, then by priority (more specific types first)
        # CARD has higher priority than PHONE to avoid card numbers being detected as phones
        priority = {"EMAIL": 0, "CARD": 1, "PHONE": 2, "PERSON": 3, "SENSITIVE_WORD": 4}
        sorted_entities = sorted(entities, key=lambda e: (e.start, priority.get(e.type, 99)))

        result = []
        last_end = -1

        for entity in sorted_entities:
            # Skip if this entity overlaps with the previous one
            if entity.start < last_end:
                continue

            result.append(entity)
            last_end = entity.end

        return result

    def detect(
        self, text: str, language: str = "en", entity_types: list[str] | None = None
    ) -> list[DetectedEntity]:
        """Detect all PII entities in the text.

        Args:
            text: Input text to scan for PII
            language: Language code for NER (default: "en")
            entity_types: Optional list of entity types to detect (e.g., ["EMAIL", "PHONE"])
                         If None, all types are detected

        Returns:
            List of detected PII entities, sorted by position
        """
        # First, detect using regex (higher priority)
        regex_entities = self._detect_by_regex(text)

        # Then, detect using NER
        ner_entities = self._detect_by_ner(text, language)

        # Detect sensitive words
        sensitive_entities = self._detect_sensitive_words(text)

        # Combine and remove overlaps
        all_entities = regex_entities + ner_entities + sensitive_entities
        unique_entities = self._remove_overlaps(all_entities)

        # Filter by entity types if specified
        if entity_types is not None:
            unique_entities = [e for e in unique_entities if e.type in entity_types]

        # Collect metrics
        for entity in unique_entities:
            PII_DETECTED_TOTAL.labels(entity_type=entity.type).inc()

        # Sort by start position
        return sorted(unique_entities, key=lambda e: e.start)


# Global detector instance (singleton)
_detector: PIIDetector | None = None


def get_detector() -> PIIDetector:
    """Get or create the global PIIDetector instance."""
    global _detector
    if _detector is None:
        _detector = PIIDetector()
    return _detector
