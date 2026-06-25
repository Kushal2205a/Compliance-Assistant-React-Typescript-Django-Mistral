import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.db.base import Base
from app.db.session import engine
from app.api.routes import health_router, reviews_router
from app.vectorstore.factory import create_vectorstore

logger = logging.getLogger(__name__)


def _preload_reranker():
    """Load the reranker model synchronously at import time,
    before any asyncio event loop exists.

    The transformers/AutoModel libraries deadlock when loaded inside
    FastAPI's lifespan or ThreadPoolExecutor. Loading at module level
    avoids that entirely.
    """
    if not settings.reranker_enabled:
        return
    try:
        from app.services.reranker_service import get_reranker
        r = get_reranker()
        logger.info("Loading reranker at import time...")
        r._load()
        logger.info("Reranker loaded at import time")
    except Exception as e:
        logger.error("Failed to load reranker at import time: %s", e)
        logger.warning("Disabling reranker for this session")
        settings.reranker_enabled = False


_preload_reranker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready")
    except Exception as e:
        logger.warning("Database unavailable (will retry on first request): %s", e)

    try:
        _ = create_vectorstore()
        logger.info("Vector store connected")
    except Exception as e:
        logger.warning("Vector store unavailable (will retry on first request): %s", e)

    yield


app = FastAPI(
    title="Compliance Evidence Evaluator",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(reviews_router)
