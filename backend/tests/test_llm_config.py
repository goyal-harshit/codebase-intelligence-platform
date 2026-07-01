"""Phase C tests: LLM config store + secret encryption (free/local providers)."""
import pytest

import db as _db
from db import LlmSetting
from llm import config, secretbox


@pytest.fixture(autouse=True)
def _clean_row():
    """Start each test with no config row (so env-fallback is testable)."""
    with _db.get_sessionmaker()() as s:
        row = s.get(LlmSetting, "default")
        if row:
            s.delete(row)
            s.commit()
    yield


def test_secretbox_roundtrip():
    token = secretbox.encrypt("s3cret-token")
    assert token != "s3cret-token"
    assert secretbox.decrypt(token) == "s3cret-token"


def test_effective_config_falls_back_to_env(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    cfg = config.effective_config()
    assert cfg["provider"] == "ollama"
    assert cfg["source"] == "env"


def test_set_and_read_config_hides_key():
    config.set_config("openai_compatible", "http://localhost:1234/v1", "local-model", "tok123")
    pub = config.public_config()
    assert pub["provider"] == "openai_compatible"
    assert pub["model"] == "local-model"
    assert pub["api_key_set"] is True
    assert "api_key" not in pub  # never exposed
    assert config.effective_config()["api_key"] == "tok123"  # decrypted internally


def test_api_key_kept_when_omitted_and_cleared_when_empty():
    config.set_config("openai_compatible", "http://x/v1", "m", "keepme")
    # provider/model change with api_key=None keeps the stored key
    config.set_config("openai_compatible", "http://x/v1", "m2", None)
    assert config.effective_config()["api_key"] == "keepme"
    # empty string clears it
    config.set_config("ollama", None, "llama3.2:latest", "")
    assert config.public_config()["api_key_set"] is False


def test_invalid_provider_rejected():
    with pytest.raises(config.ConfigError):
        config.set_config("anthropic", None, None, None)  # paid provider not allowed
