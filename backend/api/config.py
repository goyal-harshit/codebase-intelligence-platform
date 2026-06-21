"""App-level settings. Service clients read their own env vars in their own
constructors (see graph_db/vector_db/llm); this only holds API-level config."""
from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.cors_origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000"
        ).split(",")
        self.clone_dir = os.getenv("REPO_CLONE_DIR", "data/repos")
