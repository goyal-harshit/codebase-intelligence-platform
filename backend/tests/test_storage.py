"""Pluggable storage: local backend round-trip + traversal guard, and the
env-driven backend selection (Phase 3)."""
import pytest

from storage import LocalStorage, get_storage, reset_storage_cache
from storage.local import LocalStorage as LS


def test_local_put_get_exists(tmp_path):
    s = LocalStorage(str(tmp_path))
    assert not s.exists("uploads/a.zip")
    loc = s.put("uploads/a.zip", b"hello")
    assert s.exists("uploads/a.zip")
    assert s.get("uploads/a.zip") == b"hello"
    assert str(tmp_path) in loc


def test_local_rejects_traversal(tmp_path):
    s = LS(str(tmp_path))
    with pytest.raises(ValueError):
        s.put("../escape.txt", b"x")


def test_get_storage_defaults_to_local(monkeypatch):
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    reset_storage_cache()
    try:
        assert isinstance(get_storage(), LocalStorage)
    finally:
        reset_storage_cache()
