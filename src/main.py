"""FastAPI application factory, lifespan lifecycle, and entrypoint for SICRA."""

from contextlib import asynccontextmanager
import logging
import os
import threading
from typing import AsyncGenerator
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.v1 import api_v1_router
from src.database.seed import seed_database
from src.database.session import get_db, get_db_context, init_db
from src.ml.inference import InferenceEngine
from src.models.entities import Business

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sicra.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure application startup and shutdown lifecycle events."""
    logger.info("Initializing SICRA backend application...")

    # 1. Initialize relational database tables
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise

    # 2. Check if database is unpopulated and AUTO_SEED_IF_EMPTY is enabled
    auto_seed = os.getenv("AUTO_SEED_IF_EMPTY", "false").lower() in ("true", "1", "yes")
    if auto_seed:
        with get_db_context() as db:
            biz_count = db.query(Business).count()
            if biz_count == 0:
                logger.info("Empty database detected with AUTO_SEED_IF_EMPTY=true. Executing pilot seed...")
                seed_database(target_engine=db.get_bind(), quiet=True)
                logger.info("Database auto-seeding completed.")

    # 3. Warm up Stage 200 ML Inference Engine in a background thread
    def _warmup_ml() -> None:
        try:
            logger.info("Pre-warming ML inference engine in background...")
            engine = InferenceEngine()
            # Perform a test prediction to cache pipeline and models in memory
            engine.predict_daily_volume(
                business_type="FRITURA",
                num_fryers=2,
                avg_daily_customers=120,
                day_of_week=0,
                lag_7d_liters=15.0,
            )
            logger.info("ML inference engine successfully warmed up.")
        except Exception as ex:
            logger.warning(f"ML warmup encountered non-critical notice: {ex}")

    warmup_thread = threading.Thread(target=_warmup_ml, daemon=True)
    warmup_thread.start()

    yield

    logger.info("Shutting down SICRA backend application...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="SICRA Backend API",
        description=(
            "Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA) "
            "- Ingesta IoT, Alertas al 80% y Ruteo Dinámico"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration
    default_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:10000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:10000",
    ]

    custom_origins_env = os.getenv("CORS_ORIGINS")
    if custom_origins_env:
        additional_origins = [o.strip() for o in custom_origins_env.split(",") if o.strip()]
        default_origins.extend(additional_origins)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=default_origins,
        allow_origin_regex=r"^https://.*\.onrender\.com$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Health Check endpoint
    @application.get("/health", tags=["System"])
    def health_check(db: Session = Depends(get_db)):
        """Global health check endpoint confirming API service and database connectivity."""
        try:
            db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as err:
            logger.error(f"Healthcheck database connection error: {err}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "sicra-api",
                    "version": "1.0.0",
                    "database": "disconnected",
                },
            )

        return {
            "status": "healthy",
            "service": "sicra-api",
            "version": "1.0.0",
            "database": db_status,
        }

    # Mount API v1 router
    application.include_router(api_v1_router)

    return application


app = create_app()
