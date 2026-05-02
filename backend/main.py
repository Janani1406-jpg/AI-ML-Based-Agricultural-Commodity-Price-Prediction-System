from dotenv import load_dotenv
load_dotenv()
import os


"""
AI-ML Agricultural Commodity Price Prediction System
Backend API - FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from api.routes import predictions, recommendations, commodities, auth, models, reports, alerts, data
from api.models.database import create_tables
from api.utils.cache import init_cache

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up Agricultural Price Prediction System...")
    await create_tables()
    await init_cache()
    logger.info("System ready.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Agricultural Commodity Price Prediction API",
    description="AI-ML system for predicting agricultural commodity prices and generating buffer stock recommendations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://agri-dashboard.gov.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(f"method={request.method} path={request.url.path} status={response.status_code} duration={duration:.1f}ms")
    return response


# Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(commodities.router, prefix="/api/commodities", tags=["Commodities"])
app.include_router(models.router, prefix="/api/models", tags=["ML Models"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(data.router, prefix="/api/data", tags=["Data Management"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "agri-price-prediction-api", "version": "1.0.0"}


@app.get("/health/detailed", tags=["Health"])
async def detailed_health():
    from api.utils.health import get_system_metrics
    return await get_system_metrics()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": "Please contact support."})
