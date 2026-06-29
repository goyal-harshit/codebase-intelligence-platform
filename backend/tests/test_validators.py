"""Tests for the SSRF / path-traversal input validators (offline)."""
import pytest

from api.validators import (
    ValidationError,
    validate_relative_path,
    validate_repo_url,
)

# A resolver that pretends every host is a public address, so the "allowed"
# path can be tested without real DNS.
_public = lambda host: ["93.184.216.34"]
# A resolver that maps a host to an internal address (DNS-rebinding style).
_internal = lambda host: ["10.0.0.5"]


def test_allows_public_https_repo():
    assert validate_repo_url("https://github.com/org/repo.git", resolver=_public) == (
        "https://github.com/org/repo.git"
    )


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ssh://git@github.com/org/repo.git",
    "ftp://example.com/repo",
    "git://example.com/repo.git",
])
def test_rejects_non_http_schemes(url):
    with pytest.raises(ValidationError):
        validate_repo_url(url, resolver=_public)


@pytest.mark.parametrize("url", [
    "http://localhost/repo.git",
    "http://127.0.0.1/repo.git",
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata
    "http://10.0.0.5/repo.git",
    "http://192.168.1.1/repo.git",
    "http://[::1]/repo.git",
    "http://printer.local/repo.git",
])
def test_rejects_internal_targets(url):
    with pytest.raises(ValidationError):
        validate_repo_url(url, resolver=_public)


def test_rejects_public_host_resolving_to_internal_ip():
    with pytest.raises(ValidationError):
        validate_repo_url("https://evil.example.com/repo.git", resolver=_internal)


def test_rejects_unresolvable_host_fail_closed():
    def boom(host):
        raise OSError("nope")

    with pytest.raises(ValidationError):
        validate_repo_url("https://nope.invalid/repo.git", resolver=boom)


def test_relative_path_ok():
    assert validate_relative_path("backend\\api\\routes_impact.py") == (
        "backend/api/routes_impact.py"
    )


@pytest.mark.parametrize("path", [
    "../../../etc/passwd",
    "/etc/passwd",
    "C:/Windows/System32",
    "a/../../b",
    "foo\x00.py",
    "",
])
def test_relative_path_rejects_traversal(path):
    with pytest.raises(ValidationError):
        validate_relative_path(path)
