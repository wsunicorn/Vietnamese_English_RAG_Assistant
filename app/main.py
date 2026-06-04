from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.retrieval.vector_store import QdrantHybridStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.auto_create_tables:
        await init_db()
    try:
        await QdrantHybridStore(settings).ensure_collection()
    except Exception:
        # The app can still serve docs and health checks while Qdrant starts.
        pass
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Document RAG assistant with Vietnamese/English support, hybrid retrieval, citations, feedback, and metrics.",
    lifespan=lifespan,
)
app.include_router(router)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")
