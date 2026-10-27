"""Application configuration for GhostShell."""

import os
from typing import List


class Settings:
    """GhostShell runtime configuration loaded from environment variables."""

    def __init__(self):
        self.backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
        self.backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60.0"))

        raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.cors_origins: List[str] = [
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        ]


settings = Settings()
