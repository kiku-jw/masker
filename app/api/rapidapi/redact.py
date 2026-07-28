"""RapidAPI facade endpoint for PII redaction.

POST /v1/redact - Unified endpoint for RapidAPI integration.
Supports both text and JSON input modes.
"""

import time

from fastapi import APIRouter

from app.models.rapidapi_schemas import RapidAPIRedactRequest, RapidAPIRedactResponse, RedactedItem
from app.services.json_processor import process_json_with_mode
from app.services.redaction import redact_text

router = APIRouter(prefix="/v1", tags=["Main API"])


@router.post(
    "/redact",
    response_model=RapidAPIRedactResponse,
    summary="🔒 Redact PII in text or JSON",
    description="""
**Main endpoint for PII redaction.** Perfect for cleaning data before sending to LLMs like ChatGPT, Claude, etc.

## Input Modes

### Text Mode
Process plain text strings:
```json
{
  "text": "Contact John Doe at john@example.com",
  "mode": "placeholder"
}
```

### JSON Mode
Process entire JSON structures recursively (only string values are modified):
```json
{
  "json": {
    "user": {
      "name": "John Doe",
      "email": "john@example.com",
      "age": 30
    }
  },
  "mode": "placeholder"
}
```

## Redaction Modes

- **`mask`** (default): Replace PII with `***`
- **`placeholder`**: Replace PII with type placeholders:
  - `<PERSON>` for person names
  - `<EMAIL>` for email addresses
  - `<PHONE>` for phone numbers
  - `<CARD>` for credit card numbers

## Entity Filtering

Filter which PII types to redact:
```json
{
  "text": "John Doe's email is john@example.com",
  "mode": "placeholder",
  "entities": ["EMAIL"]  // Only redact emails
}
```

**Supported entity types:** `PERSON`, `EMAIL`, `PHONE`, `CARD`

## Example Response

```json
{
  "redacted_text": "Contact <PERSON> at <EMAIL>",
  "redacted_json": null,
  "items": [
    {
      "entity_type": "PERSON",
      "path": null,
      "start": 8,
      "end": 16,
      "score": 0.85
    },
    {
      "entity_type": "EMAIL",
      "path": null,
      "start": 20,
      "end": 36,
      "score": 1.0
    }
  ],
  "processing_time_ms": 15.29
}
```
""",
)
async def rapidapi_redact(request: RapidAPIRedactRequest) -> RapidAPIRedactResponse:
    """Redact PII entities in the provided text or JSON.

    This endpoint is designed for RapidAPI integration and provides:
    - Flexible input (text or JSON)
    - Flexible redaction modes (mask/placeholder)
    - Entity type filtering
    - Confidence scores for each detection
    - Processing time measurement
    """
    start_time = time.perf_counter()

    # Convert entities filter to list of strings if provided
    entities_filter = list(request.entities) if request.entities else None

    if request.is_json_mode:
        # JSON mode
        redacted_data, json_entities = process_json_with_mode(
            data=request.json,
            language=request.language,
            mode=request.mode,
            entities_filter=entities_filter,
        )

        processing_time_ms = (time.perf_counter() - start_time) * 1000

        items = [
            RedactedItem(
                entity_type=e.type,
                path=e.path,
                start=e.start,
                end=e.end,
                score=1.0 if e.type in ("EMAIL", "PHONE", "CARD", "SENSITIVE_WORD") else 0.85,
            )
            for e in json_entities
        ]

        return RapidAPIRedactResponse(
            redacted_text=None,
            redacted_json=redacted_data,
            items=items,
            processing_time_ms=round(processing_time_ms, 2),
        )
    else:
        # Text mode
        redacted_text_result, redacted_items = redact_text(
            text=request.text,
            language=request.language,
            entities_filter=entities_filter,
            mode=request.mode,
        )

        processing_time_ms = (time.perf_counter() - start_time) * 1000

        items = [
            RedactedItem(
                entity_type=item.entity_type,
                path=None,
                start=item.start,
                end=item.end,
                score=item.score,
            )
            for item in redacted_items
        ]

        return RapidAPIRedactResponse(
            redacted_text=redacted_text_result,
            redacted_json=None,
            items=items,
            processing_time_ms=round(processing_time_ms, 2),
        )
