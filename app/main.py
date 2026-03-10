"""Masker API - PII Redaction & Text Anonymization Service.

Main FastAPI application entry point.
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.proxy import router as proxy_router
from app.api.rapidapi.redact import router as rapidapi_router
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import log_request, logger
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.schemas import ErrorResponse, HealthResponse
from app.services.pii_detector import get_detector

# Global start time
APP_START_TIME = time.time()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler - load models on startup."""
    global APP_START_TIME
    APP_START_TIME = time.time()

    logger.info("Starting Masker API...")
    # Pre-load the PII detector to warm up spaCy models
    get_detector()
    logger.info("PII detector initialized")
    yield
    logger.info("Shutting down Masker API...")


app = FastAPI(
    title=settings.api_title,
    description="""
    **Masker API** - Privacy-first PII Redaction & Text Anonymization for LLMs.

    Remove personal information from text and JSON before sending to ChatGPT, Claude, or any LLM.

    ## 🔒 Privacy First
    - **No data storage** - All processing is in-memory
    - **No content logging** - Only metadata is logged
    - **Stateless** - Each request is independent

    ## 🚀 Quick Start

    **Text Mode:**
    ```json
    POST /v1/redact
    {
      "text": "Contact John Doe at john@example.com",
      "mode": "placeholder"
    }
    ```

    **JSON Mode:**
    ```json
    POST /v1/redact
    {
      "json": {"user": {"name": "John Doe", "email": "john@example.com"}},
      "mode": "placeholder"
    }
    ```

    ## 📚 Endpoints

    - **`POST /v1/redact`** - Main endpoint for PII redaction (supports text & JSON)
    - **`POST /api/v1/detect`** - Detect PII without modifying content
    - **`POST /api/v1/mask`** - Mask PII with `***`
    - **`POST /api/v1/redact`** - Redact PII with `[REDACTED]`
    - **`GET /health`** - Health check

    ## 📖 Full Documentation

    See [Wiki](https://github.com/kiku-jw/masker/wiki) for complete documentation.
    """,
    version=settings.api_version,
    lifespan=lifespan,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        413: {"model": ErrorResponse, "description": "Request Entity Too Large"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    tags_metadata=[
        {
            "name": "Main API",
            "description": "**Main endpoint for PII redaction.** Supports both text and JSON input modes. Perfect for cleaning data before sending to LLMs.",
        },
        {
            "name": "PII Detection",
            "description": "**Detect PII entities** without modifying the content. Returns list of detected entities with their types and positions.",
        },
        {
            "name": "PII Masking",
            "description": "**Mask PII entities** by replacing them with asterisks (`***`). Preserves structure in JSON mode.",
        },
        {
            "name": "PII Redaction",
            "description": "**Redact PII entities** by replacing them with `[REDACTED]`. Preserves structure in JSON mode.",
        },
        {
            "name": "Health",
            "description": "**Health check endpoint.** No authentication required. Returns service status and version.",
        },
        {
            "name": "Root",
            "description": "API root endpoint. Redirects to documentation.",
        },
    ],
)


# Request ID middleware - add unique ID to each request for tracking
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracking and debugging."""

    async def dispatch(self, request: Request, call_next):
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Add to request state for logging
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestIDMiddleware)

# Metrics middleware
app.add_middleware(MetricsMiddleware)

# Rate limiting middleware - protect API from abuse
# Important for RapidAPI: 60 req/min per IP, 1000 req/min global
app.add_middleware(RateLimitMiddleware)

# CORS middleware - allow cross-origin requests
# This is important for browser-based clients and RapidAPI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, consider restricting to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Processing-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log request metadata without exposing content."""
    start_time = time.perf_counter()

    # Get content length from headers (before reading body)
    content_length = int(request.headers.get("content-length", 0))

    # Get request ID from state (set by RequestIDMiddleware)
    request_id = getattr(request.state, "request_id", "unknown")

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Add processing time header
    response.headers["X-Processing-Time"] = f"{duration_ms:.2f}ms"

    log_request(
        logger=logger,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        content_length=content_length,
        duration_ms=duration_ms,
        request_id=request_id,
    )

    return response


@app.middleware("http")
async def size_limit_middleware(request: Request, call_next):
    """Reject requests that exceed the maximum allowed payload size."""
    content_length = int(request.headers.get("content-length", 0))

    if content_length > settings.max_payload_size:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={
                "detail": f"Request body too large. Maximum allowed payload size is {settings.max_payload_size} bytes ({settings.max_payload_size // 1024}KB)."
            },
        )

    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with clean messages."""
    errors = exc.errors()

    # Extract first error message for simplicity
    if errors:
        first_error = errors[0]
        loc = " -> ".join(str(item) for item in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation error")
        detail = f"{loc}: {msg}" if loc else msg
    else:
        detail = "Validation error"

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, _exc: Exception):
    """Handle unexpected exceptions without exposing details."""
    logger.exception("Unexpected error processing request")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get(
    "/",
    tags=["Root"],
    summary="🏠 API root endpoint",
    description="Redirects to interactive API documentation at `/docs`.",
)
async def root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="💚 Health check endpoint",
    description="""
**Check if the service is running and healthy.**

No authentication required. Returns service status and version.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```
""",
)
async def health_check() -> HealthResponse:
    """Check if the service is running."""
    uptime = time.time() - APP_START_TIME

    # Check if detector is loaded
    detector_status = "ready"
    try:
        get_detector()
    except Exception:
        detector_status = "error"

    return HealthResponse(
        status="ok",
        version=settings.api_version,
        uptime_seconds=round(uptime, 2),
        components={"pii_detector": detector_status, "rate_limiter": "active"},
    )


@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="📊 Prometheus metrics",
    description="Prometheus-compatible metrics endpoint for monitoring and observability.",
    include_in_schema=False,  # Hide from main API docs
)
async def metrics():
    """Export Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Include API v1 routes (canonical path)
app.include_router(v1_router, prefix="/v1")

# Include RapidAPI facade routes (also under /v1)
# Note: rapidapi_router already has /v1 prefix, so check for conflicts
# The rapidapi /v1/redact is more feature-rich, keep it alongside /v1/redact from v1_router
app.include_router(rapidapi_router)

# Include LLM Proxy routes (/v1/chat/completions)
app.include_router(proxy_router)

# Legacy routes (deprecated - will be removed in 6 months)
# Include same v1_router under /api/v1 for backward compatibility
app.include_router(v1_router, prefix="/api/v1", deprecated=True, tags=["Legacy"])
