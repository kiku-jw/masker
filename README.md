<div align="center">
  <img src="https://github.com/user-attachments/assets/fe7b47e8-6989-4161-8b17-5d77d1312fa4" alt="image" width="120" height="120">
  
  <h1 align="center">Masker</h1>
</div>

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![spaCy](https://img.shields.io/badge/spaCy-NER-09A3D5.svg)](https://spacy.io)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](Dockerfile)

**PII redaction API for LLMs.** Remove personal data before sending to ChatGPT, Claude, or any AI.

**[Open the project site](https://kikuai-lab.github.io/masker/)** ·
**[Run locally](#quick-start)**

[Docs](#llm-proxy-openai-compatible) · [Examples](#what-it-does) · [API quickstart](#quick-start)

## What it does

```
Input:  "Contact John Doe at john@example.com"
Output: "Contact <PERSON> at <EMAIL>"
```

Masker detects and redacts:
- **EMAIL** — email addresses
- **PHONE** — phone numbers  
- **CARD** — credit card numbers
- **PERSON** — person names (AI-powered)
- **SENSITIVE_WORD** — custom words and phrases configured by the operator

## Quick Start

```bash
docker run -p 8000:8000 ghcr.io/kikuai-lab/masker
```

```bash
curl -X POST http://localhost:8000/v1/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "Email me at john@example.com", "mode": "placeholder"}'
```

## LLM Proxy (OpenAI-compatible)

Drop-in replacement for `/v1/chat/completions` that automatically redacts PII:

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-openai-key",
    default_headers={"X-Api-Key": "your-masker-key"}
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "My email is john@example.com"}]
)
# PII redacted before reaching OpenAI
```

## Features

- **Text & JSON** — process plain text or nested JSON
- **Policy system** — configure mask/drop/placeholder per PII type
- **Audit logging** — JSONL logs without storing raw text
- **Fail modes** — `closed` (block) or `open` (pass-through)
- **Multi-tenant** — API key authentication
- **Multi-language** — English & Russian NER

## Installation

```bash
git clone https://github.com/KikuAI-Lab/masker.git
cd masker
cp .env.example .env
docker-compose up -d
```

## Configuration

```bash
MASKER_API_KEYS=sk-key1:tenant1,sk-key2:tenant2
MASKER_UPSTREAM_URL=https://api.openai.com/v1/chat/completions
MASKER_DEFAULT_FAIL_MODE=closed
MASKER_SENSITIVE_WORDS=secret,confidential,internal project
```

`MASKER_SENSITIVE_WORDS` is a comma-separated, case-insensitive list.

See [.env.example](.env.example) for all options.

## Documentation

📖 **[Wiki](https://github.com/KikuAI-Lab/masker/wiki)** — full documentation

- [Quick Start](https://github.com/KikuAI-Lab/masker/wiki/Quick-Start)
- [API Reference](https://github.com/KikuAI-Lab/masker/wiki/API-Reference)
- [LLM Proxy](https://github.com/KikuAI-Lab/masker/wiki/LLM-Proxy)
- [Privacy Policy](https://github.com/KikuAI-Lab/masker/wiki/Privacy-Policy)

## API

| Endpoint | Description |
|----------|-------------|
| `POST /v1/redact` | Redact PII from text or JSON |
| `POST /v1/chat/completions` | OpenAI-compatible proxy |
| `GET /health` | Health check |
| `GET /metrics` | Prometheus metrics |

## Security & Architecture
<br>

> **Stateless by Design.**
> Masker is a firewall, not a storage bucket.

*   ✅ **No raw payload storage by design** — Payloads are processed in RAM and are not intentionally persisted.
*   ✅ **Local PII detection path** — Redaction logic does not require third-party AI calls.
*   ✅ **Self-hostable boundary** — The redaction service can run without internet access; proxy mode still calls the configured upstream provider.

📖 Read about our **[Stateless Architecture](docs/STATELESS_ARCHITECTURE.md)** to understand the intended privacy boundary and deployment assumptions.

## Follow the work

Project notes and new tools: [Telegram](https://t.me/kiku_ai) ·
[LinkedIn](https://www.linkedin.com/in/kiku-jw/) ·
[KikuAI](https://kikuai.dev/)

## License

AGPL-3.0 — [KikuAI OÜ](https://kikuai.dev)

<!-- author-links:start -->
<p align="center">
  <a href="https://kikuai.dev/"><img src="https://img.shields.io/badge/Website-kikuai.dev-111827?style=for-the-badge&logo=safari&logoColor=white" alt="KikuAI website"></a>
  <a href="https://t.me/kiku_ai"><img src="https://img.shields.io/badge/Telegram-%40kiku__ai-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram @kiku_ai"></a>
  <a href="https://github.com/kiku-jw"><img src="https://img.shields.io/badge/GitHub-%40kiku--jw-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @kiku-jw"></a>
</p>
<p align="center">
  <sub>Follow new projects and updates from <a href="https://github.com/kiku-jw">@kiku-jw</a>.</sub>
</p>
<!-- author-links:end -->
