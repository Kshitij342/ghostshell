"""GhostShell — Haunted AI Terminal backend entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.routes import chat, health, ollama

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ghostshell")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GhostShell backend initialized.")
    logger.info("Listening on %s:%s", settings.backend_host, settings.backend_port)
    logger.info("Ollama target URL: %s (Default Model: %s)", settings.ollama_base_url, settings.ollama_model)
    logger.info("Allowed CORS origins: %s", settings.cors_origins)
    yield


app = FastAPI(
    title="GhostShell — Haunted AI Terminal",
    description="Your terminal has a ghost. It knows your code. Local AI assistant for developers.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Restrictive CORS configured for local development Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Register route modules
app.include_router(health.router)
app.include_router(ollama.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )

