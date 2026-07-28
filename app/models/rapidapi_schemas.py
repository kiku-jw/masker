"""Pydantic schemas for RapidAPI facade endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings

# Supported entity types for filtering
EntityTypeFilter = Literal["PERSON", "EMAIL", "PHONE", "CARD", "SENSITIVE_WORD"]

# Redaction modes
RedactionMode = Literal["mask", "placeholder"]


class RapidAPIRedactRequest(BaseModel):
    """Request schema for RapidAPI /v1/redact endpoint.

    Supports both text and JSON input modes.
    Either 'text' or 'json' must be provided, but not both.
    """

    text: str | None = Field(
        default=None,
        min_length=1,
        max_length=settings.max_text_size,
        description="Text to process for PII redaction",
    )
    json: Any | None = Field(
        default=None, description="JSON object/array to process recursively (string values only)"
    )
    language: Literal["en", "ru"] = Field(
        default="en", description="Language of the content (en or ru)"
    )
    entities: list[EntityTypeFilter] | None = Field(
        default=None,
        description="List of entity types to redact. If not provided, all types are redacted.",
    )
    mode: RedactionMode = Field(
        default="mask",
        description="Redaction mode: 'mask' replaces with ***, 'placeholder' replaces with <TYPE>",
    )

    @model_validator(mode="after")
    def validate_input_mode(self) -> "RapidAPIRedactRequest":
        """Ensure exactly one of text or json is provided."""
        if self.text is None and self.json is None:
            raise ValueError("Either 'text' or 'json' must be provided")
        if self.text is not None and self.json is not None:
            raise ValueError("Provide either 'text' or 'json', not both")
        return self

    @property
    def is_json_mode(self) -> bool:
        """Check if request is in JSON mode."""
        return self.json is not None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Hello, my name is John Doe and my email is john@example.com",
                    "language": "en",
                    "entities": ["PERSON", "EMAIL"],
                    "mode": "placeholder",
                },
                {
                    "json": {
                        "user": {"name": "John Doe", "email": "john@example.com"},
                        "message": "Call me at +1-555-123-4567",
                    },
                    "language": "en",
                    "mode": "mask",
                },
            ]
        }
    }


class RedactedItem(BaseModel):
    """Schema for a single redacted item in the response."""

    entity_type: str = Field(
        ...,
        description=("Type of the detected entity (PERSON, EMAIL, PHONE, CARD, SENSITIVE_WORD)"),
    )
    path: str | None = Field(
        default=None, description="JSON path to the field (only for JSON mode)"
    )
    start: int = Field(..., ge=0, description="Start position in the original text/field")
    end: int = Field(..., ge=0, description="End position in the original text/field")
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (1.0 for regex matches, NER model score for PERSON)",
    )


class RapidAPIRedactResponse(BaseModel):
    """Response schema for RapidAPI /v1/redact endpoint (text mode)."""

    redacted_text: str | None = Field(
        default=None, description="Text with PII replaced (text mode only)"
    )
    redacted_json: Any | None = Field(
        default=None, description="JSON with PII replaced in string values (JSON mode only)"
    )
    items: list[RedactedItem] = Field(
        default_factory=list, description="List of detected and redacted entities"
    )
    processing_time_ms: float = Field(..., ge=0, description="Processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "redacted_text": "Hello, my name is <PERSON> and my email is <EMAIL>",
                    "redacted_json": None,
                    "items": [
                        {
                            "entity_type": "PERSON",
                            "path": None,
                            "start": 18,
                            "end": 26,
                            "score": 0.85,
                        }
                    ],
                    "processing_time_ms": 45.2,
                },
                {
                    "redacted_text": None,
                    "redacted_json": {
                        "user": {"name": "***", "email": "***"},
                        "message": "Call me at ***",
                    },
                    "items": [
                        {
                            "entity_type": "PERSON",
                            "path": "user.name",
                            "start": 0,
                            "end": 8,
                            "score": 0.85,
                        }
                    ],
                    "processing_time_ms": 52.1,
                },
            ]
        }
    }
