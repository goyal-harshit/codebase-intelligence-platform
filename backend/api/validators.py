"""Input validators for user-supplied repo URLs and file paths.

Kept dependency-free and the DNS resolver injectable so these can be unit-tested
offline (no real network), matching the injectable style used elsewhere in this
package.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Callable, Iterable
from urllib.parse import urlparse

ALLOWED_URL_SCHEMES = {"http", "https"}

# Hostnames that must never be cloned from, independent of DNS resolution.
_BLOCKED_HOSTNAMES = {
    "localhost",
    "ip6-localhost",
    "metadata",
    "metadata.google.internal",
}

Resolver = Callable[[str], Iterable[str]]


class ValidationError(ValueError):
    """Raised when user input fails a security check."""


def _default_resolver(host: str) -> list[str]:
    # Return every IP the host resolves to (v4 + v6).
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # un-parseable -> treat as unsafe
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_repo_url(url: str, resolver: Resolver = _default_resolver) -> str:
    """Allow-list a clone URL and block SSRF to internal/loopback ranges.

    Fails closed: a host that cannot be resolved is rejected, so the clone step
    never reaches out to something we could not vet.
    """
    if not url or not url.strip():
        raise ValidationError("repo_url is empty")
    url = url.strip()

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        raise ValidationError(
            f"repo_url scheme {parsed.scheme!r} not allowed; use http(s)"
        )
    host = parsed.hostname
    if not host:
        raise ValidationError("repo_url has no host")
    if host.lower() in _BLOCKED_HOSTNAMES or host.lower().endswith(".local"):
        raise ValidationError(f"repo_url host {host!r} is not allowed")

    # If the host is a literal IP, check it directly; otherwise resolve it.
    try:
        ipaddress.ip_address(host)
        candidates: Iterable[str] = [host]
    except ValueError:
        try:
            candidates = list(resolver(host))
        except Exception as exc:  # noqa: BLE001 - any resolution failure = reject
            raise ValidationError(f"repo_url host {host!r} could not be resolved") from exc
        if not candidates:
            raise ValidationError(f"repo_url host {host!r} resolved to nothing")

    for ip in candidates:
        if _is_blocked_ip(ip):
            raise ValidationError(
                f"repo_url host {host!r} resolves to a blocked address ({ip})"
            )
    return url


def validate_relative_path(path: str) -> str:
    """Guard a repo-relative file path against traversal/absolute escapes.

    The impact endpoint feeds ``file_path`` straight into a graph lookup; this
    rejects anything that is absolute, contains a ``..`` segment, a NUL byte, or
    a Windows drive letter, and normalises separators to forward slashes.
    """
    if not path or not path.strip():
        raise ValidationError("file_path is empty")
    if "\x00" in path:
        raise ValidationError("file_path contains a NUL byte")

    normalised = path.replace("\\", "/").strip()
    if normalised.startswith("/"):
        raise ValidationError("file_path must be repo-relative, not absolute")
    if len(normalised) >= 2 and normalised[1] == ":":
        raise ValidationError("file_path must not contain a drive letter")
    if any(segment == ".." for segment in normalised.split("/")):
        raise ValidationError("file_path must not contain '..' segments")
    return normalised
