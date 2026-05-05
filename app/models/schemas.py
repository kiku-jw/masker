"""Pydantic schemas for API request/response validation."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings

# Entity types
EntityType = Literal["EMAIL", "PHONE", "CARD", "PERSON", "SENSITIVE_WORD"]


class TextRequest(BaseModel):
    """Request schema for text-only processing endpoints (legacy compatibility)."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_text_size,
        description="Text to process for PII detection",
    )
    language: Literal["en", "ru"] = Field(
        default="en", description="Language of the text (en or ru)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Contact John Doe at john.doe@example.com or +1-555-123-4567",
                    "language": "en",
                }
            ]
        }
    }


class UnifiedRequest(BaseModel):
    """Request schema supporting both text and JSON input.

    Either 'text' or 'json' must be provided, but not both.
    - text: Plain text string to process
    - json: JSON object/array with string values to process recursively
    """

    text: str | None = Field(
        default=None,
        min_length=1,
        max_length=settings.max_text_size,
        description="Text to process for PII detection",
    )
    json: Any | None = Field(
        default=None, description="JSON object/array to process recursively (string values only)"
    )
    language: Literal["en", "ru"] = Field(
        default="en", description="Language of the content (en or ru)"
    )
    entities: list[EntityType] | None = Field(
        default=None,
        description="Filter to detect only specific entity types (e.g., ['EMAIL', 'PHONE'])",
    )

    @model_validator(mode="after")
    def validate_input_mode(self) -> "UnifiedRequest":
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
                {"text": "Contact John Doe at john.doe@example.com", "language": "en"},
                {
                    "json": {
                        "user": {"name": "John Doe", "email": "john@example.com"},
                        "message": "Call me at +1-555-123-4567",
                    },
                    "language": "en",
                },
            ]
        }
    }


class DetectedEntity(BaseModel):
    """Schema for a detected PII entity."""

    type: EntityType = Field(..., description="Type of PII entity detected")
    value: str = Field(..., description="Original value of the detected entity")
    start: int = Field(..., ge=0, description="Start position of the entity in the text")
    end: int = Field(..., ge=0, description="End position of the entity in the text")


class MaskedEntity(DetectedEntity):
    """Schema for a detected and masked PII entity."""

    masked_value: str = Field(..., description="Masked/redacted value that replaced the original")


class JsonFieldEntity(BaseModel):
    """Schema for a detected entity within a JSON field."""

    path: str = Field(
        ..., description="JSON path to the field (e.g., 'user.email' or 'items[0].name')"
    )
    type: EntityType = Field(..., description="Type of PII entity detected")
    value: str = Field(..., description="Original value of the detected entity")
    start: int = Field(..., ge=0, description="Start position within the field value")
    end: int = Field(..., ge=0, description="End position within the field value")


class DetectResponse(BaseModel):
    """Response schema for /detect endpoint (text mode)."""

    entities: list[DetectedEntity] = Field(
        default_factory=list, description="List of detected PII entities"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entities": [
                        {"type": "EMAIL", "value": "john.doe@example.com", "start": 20, "end": 40}
                    ]
                }
            ]
        }
    }


class DetectJsonResponse(BaseModel):
    """Response schema for /detect endpoint (JSON mode)."""

    entities: list[JsonFieldEntity] = Field(
        default_factory=list, description="List of detected PII entities with JSON paths"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entities": [
                        {
                            "path": "user.email",
                            "type": "EMAIL",
                            "value": "john@example.com",
                            "start": 0,
                            "end": 16,
                        }
                    ]
                }
            ]
        }
    }


class MaskResponse(BaseModel):
    """Response schema for /mask and /redact endpoints (text mode)."""

    text: str = Field(..., description="Processed text with PII masked/redacted")
    entities: list[MaskedEntity] = Field(
        default_factory=list, description="List of detected and masked PII entities"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Contact *** at ***",
                    "entities": [
                        {
                            "type": "PERSON",
                            "value": "John Doe",
                            "masked_value": "***",
                            "start": 8,
                            "end": 16,
                        }
                    ],
                }
            ]
        }
    }


class MaskJsonResponse(BaseModel):
    """Response schema for /mask and /redact endpoints (JSON mode)."""

    json: Any = Field(..., description="Processed JSON with PII masked/redacted in string values")
    entities: list[JsonFieldEntity] = Field(
        default_factory=list, description="List of detected PII entities with JSON paths"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "json": {"user": {"name": "***", "email": "***"}, "message": "Call me at ***"},
                    "entities": [
                        {
                            "path": "user.name",
                            "type": "PERSON",
                            "value": "John Doe",
                            "start": 0,
                            "end": 8,
                        }
                    ],
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(default="ok", description="Service status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    components: dict[str, str] = Field(
        default_factory=dict,
        description="Status of individual components (e.g., 'pii_detector': 'ready')",
    )


class ErrorResponse(BaseModel):
    """Response schema for error responses."""

    detail: str = Field(..., description="Error description")
