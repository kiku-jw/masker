"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All settings can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(env_prefix="MASKER_")

    # API settings
    api_title: str = "Masker API"
    api_description: str = "PII Redaction & Text Anonymization API for LLMs and JSON"
    api_version: str = "1.0.0"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Request limits
    max_text_size: int = 32 * 1024  # 32KB for text field
    max_payload_size: int = 64 * 1024  # 64KB for entire JSON payload
    request_timeout: int = 10  # 10s default timeout for intensive operations

    # Supported languages for NER
    supported_languages: list[str] = ["en", "ru"]
    default_language: str = "en"

    # Masking/redaction tokens (configurable defaults)
    mask_token: str = "***"
    redact_token: str = "[REDACTED]"

    # Placeholder templates for typed redaction
    placeholder_person: str = "<PERSON>"
    placeholder_email: str = "<EMAIL>"
    placeholder_phone: str = "<PHONE>"
    placeholder_card: str = "<CARD>"
    placeholder_sensitive_word: str = "<SENSITIVE_WORD>"

    # Sensitive word detection (comma-separated list)
    sensitive_words: str = ""

    @property
    def sensitive_word_list(self) -> list[str]:
        """Parse comma-separated sensitive words."""
        return [w.strip() for w in self.sensitive_words.split(",") if w.strip()]

    # ========================================
    # Safe-to-LLM Proxy Settings
    # ========================================

    # Upstream LLM settings
    upstream_url: str = "https://api.openai.com/v1/chat/completions"
    upstream_timeout: int = 60  # Timeout for upstream requests in seconds

    # API Keys (format: "key1:tenant1,key2:tenant2")
    api_keys: str = ""

    # Policy settings
    policies_dir: str = "./policies"
    default_policy_id: str = "default"
    default_fail_mode: str = "closed"  # "closed" or "open"

    # Audit settings
    audit_dir: str = "./audit"
    audit_enabled: bool = True


# Global settings instance
settings = Settings()
