"""System health metrics endpoint."""
import psutil, os
from datetime import datetime

async def get_system_metrics() -> dict:
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_pct": psutil.cpu_percent(interval=1),
            "memory_pct": psutil.virtual_memory().percent,
            "disk_pct": psutil.disk_usage("/").percent,
        },
        "services": {
            "database": await _check_db(),
            "redis": await _check_redis(),
        },
        "model_registry": os.path.exists(os.getenv("MODEL_REGISTRY_PATH", "/app/models")),
    }

async def _check_db() -> str:
    try:
        from api.models.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return "healthy"
    except Exception as e:
        return f"error: {e}"

async def _check_redis() -> str:
    try:
        from api.utils.cache import _redis
        if _redis: await _redis.ping(); return "healthy"
        return "not_connected"
    except Exception as e:
        return f"error: {e}"
