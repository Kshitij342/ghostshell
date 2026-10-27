"""Health check endpoint for GhostShell."""

from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def get_health():
    """Return backend operational status."""
    return {
        "status": "healthy",
        "app": "GhostShell",
        "tagline": "Your terminal has a ghost. It knows your code.",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
