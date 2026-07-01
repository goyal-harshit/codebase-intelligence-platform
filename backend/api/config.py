"""App-level settings. Service clients read their own env vars in their own
constructors (see graph_db/vector_db/llm); this only holds API-level config."""
from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.cors_origins = os.getenv(
            "CORS_ORIGINS",
            ",".join(
                [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://localhost:3100",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:3001",
                    "http://127.0.0.1:3100",
                ]
            ),
        ).split(",")
        self.cors_origin_regex = os.getenv(
            "CORS_ORIGIN_REGEX",
            r"^http://(localhost|127\.0\.0\.1):(3[0-9]{3}|81[0-9]{2})$",
        )
        self.clone_dir = os.getenv("REPO_CLONE_DIR", "data/repos")
        # When set, every data route requires a matching X-API-Key header.
        # When unset, the API is open (dev mode) and main.py logs a warning.
        self.api_key = os.getenv("API_KEY") or None
