"""Tests for sensitive word detection."""

from fastapi.testclient import TestClient

from app.core.config import settings


class TestSensitiveWords:
    """Tests for SENSITIVE_WORD entity detection and masking."""

    def test_detect_sensitive_word(self, client: TestClient, monkeypatch):
        """Should detect configured sensitive words."""
        monkeypatch.setattr(settings, "sensitive_words", "secret,confidential")
        response = client.post("/api/v1/detect", json={"text": "This is a secret document"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 1
        assert sw[0]["value"] == "secret"

    def test_detect_multiple_sensitive_words(self, client: TestClient, monkeypatch):
        """Should detect multiple different sensitive words."""
        monkeypatch.setattr(settings, "sensitive_words", "secret,confidential")
        response = client.post("/api/v1/detect", json={"text": "This is secret and confidential"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 2
        values = {e["value"].lower() for e in sw}
        assert "secret" in values
        assert "confidential" in values

    def test_case_insensitive_detection(self, client: TestClient, monkeypatch):
        """Should detect words regardless of case."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        response = client.post("/api/v1/detect", json={"text": "This is SECRET and Secret"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 2

    def test_word_boundary_prevents_substring_match(self, client: TestClient, monkeypatch):
        """Should not match sensitive words inside other words."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        response = client.post("/api/v1/detect", json={"text": "This is a secretory gland"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 0

    def test_empty_config_no_detection(self, client: TestClient, monkeypatch):
        """Should not detect sensitive words when config is empty."""
        monkeypatch.setattr(settings, "sensitive_words", "")
        response = client.post("/api/v1/detect", json={"text": "This is a secret document"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 0

    def test_mask_sensitive_word(self, client: TestClient, monkeypatch):
        """Should mask sensitive words with asterisks."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        response = client.post("/api/v1/mask", json={"text": "This is a secret document"})

        assert response.status_code == 200
        data = response.json()
        assert "***" in data["text"]
        assert "secret" not in data["text"]

    def test_redact_sensitive_word(self, client: TestClient, monkeypatch):
        """Should redact sensitive words with [REDACTED]."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        response = client.post("/api/v1/redact", json={"text": "This is a secret document"})

        assert response.status_code == 200
        data = response.json()
        assert "[REDACTED]" in data["text"]
        assert "secret" not in data["text"]

    def test_overlap_existing_entity_wins(self, client: TestClient, monkeypatch):
        """Should prefer EMAIL over SENSITIVE_WORD on overlap."""
        monkeypatch.setattr(settings, "sensitive_words", "test")
        response = client.post("/api/v1/detect", json={"text": "Contact test@example.com"})

        assert response.status_code == 200
        data = response.json()
        types = [e["type"] for e in data["entities"]]
        assert "EMAIL" in types
        assert "SENSITIVE_WORD" not in types

    def test_cyrillic_word_boundary(self, client: TestClient, monkeypatch):
        """Should detect Cyrillic sensitive words."""
        monkeypatch.setattr(settings, "sensitive_words", "СВО,спецоперация")
        response = client.post("/api/v1/detect", json={"text": "Новости о СВО и спецоперации"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) >= 1

    def test_sensitive_word_at_text_boundaries(self, client: TestClient, monkeypatch):
        """Should detect words at start and end of text."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        response = client.post("/api/v1/detect", json={"text": "secret is the secret"})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 2
        assert sw[0]["start"] == 0

    def test_sensitive_word_entity_positions(self, client: TestClient, monkeypatch):
        """Should return correct positions for sensitive words."""
        monkeypatch.setattr(settings, "sensitive_words", "secret")
        text = "The secret is here"
        response = client.post("/api/v1/detect", json={"text": text})

        assert response.status_code == 200
        data = response.json()
        sw = [e for e in data["entities"] if e["type"] == "SENSITIVE_WORD"]
        assert len(sw) == 1
        assert text[sw[0]["start"] : sw[0]["end"]] == "secret"
