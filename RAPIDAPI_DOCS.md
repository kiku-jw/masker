# Masker API - RapidAPI Documentation

## Overview

Masker is a **PII Redaction API** that automatically detects and masks personally identifiable information in text and JSON. Designed for high-throughput LLM pipelines, analytics preprocessing, and GDPR/CCPA compliance.

---

## Quick Start

### cURL
```bash
curl -X POST "https://masker-api.p.rapidapi.com/v1/redact" \
  -H "X-RapidAPI-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact john@example.com or call +1-555-123-4567",
    "mode": "mask"
  }'
```

### Python
```python
import requests

url = "https://masker-api.p.rapidapi.com/v1/redact"
headers = {
    "X-RapidAPI-Key": "YOUR_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "text": "My email is john@example.com",
    "mode": "placeholder"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
# {"text": "My email is <EMAIL>", "entities": [...]}
```

### JavaScript (Node.js)
```javascript
const axios = require('axios');

const response = await axios.post(
  'https://masker-api.p.rapidapi.com/v1/redact',
  {
    text: 'Contact john@example.com',
    mode: 'mask'
  },
  {
    headers: {
      'X-RapidAPI-Key': 'YOUR_API_KEY',
      'Content-Type': 'application/json'
    }
  }
);

console.log(response.data);
// { text: 'Contact ***', entities: [...] }
```

---

## Endpoints

### POST /v1/redact

Detect and redact PII from text or JSON.

#### Request Body

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | One of text/json | - | Plain text to redact |
| `json` | object | One of text/json | - | JSON object to redact |
| `mode` | string | No | `mask` | Redaction mode: `mask`, `placeholder`, `redact` |
| `language` | string | No | `en` | Language: `en`, `ru` |
| `entities` | array | No | all | Entity types to redact |

#### Redaction Modes

| Mode | Example Input | Example Output |
|------|---------------|----------------|
| `mask` | `john@example.com` | `***` |
| `placeholder` | `john@example.com` | `<EMAIL>` |
| `redact` | `john@example.com` | `[REDACTED]` |

#### Response

```json
{
  "text": "Contact ***",
  "entities": [
    {
      "type": "EMAIL",
      "original": "john@example.com",
      "redacted": "***",
      "start": 8,
      "end": 24
    }
  ],
  "processing_time_ms": 45.2
}
```

---

## Supported PII Types

| Type | Description | Example |
|------|-------------|---------|
| `EMAIL` | Email addresses | john@example.com |
| `PHONE` | Phone numbers (international) | +1-555-123-4567 |
| `CARD` | Credit/debit cards | 4111-1111-1111-1111 |
| `PERSON` | Person names (NER-based) | John Doe |

---

## JSON Mode

Process entire JSON structures recursively:

```json
{
  "json": {
    "user": {
      "email": "test@example.com",
      "profile": {
        "phone": "+1-555-123-4567"
      }
    }
  },
  "mode": "mask"
}
```

Response:
```json
{
  "json": {
    "user": {
      "email": "***",
      "profile": {
        "phone": "***"
      }
    }
  },
  "entities": [...]
}
```

---

## Filter Entities

Redact only specific entity types:

```json
{
  "text": "Email john@example.com, phone +1-555-123-4567",
  "entities": ["EMAIL"],
  "mode": "mask"
}
```

Result: Only email is masked, phone is preserved.

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request (missing text/json) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

| Tier | Requests/Month | Requests/Minute |
|------|----------------|-----------------|
| Basic (Free) | 100 | 10 |
| Pro | 10,000 | 100 |
| Ultra | 50,000 | 500 |
| Mega | 250,000 | 2,000 |

---

## Privacy & Security

- **Stateless**: No data storage or logging
- **No training**: Your data is never used for ML training
- **GDPR/CCPA**: Compliant by design
- **Open Source**: https://github.com/kiku-jw/masker

---

## Support

- Documentation: https://github.com/kiku-jw/masker/wiki
- Email: support@kikuai.dev
- GitHub Issues: https://github.com/kiku-jw/masker/issues
