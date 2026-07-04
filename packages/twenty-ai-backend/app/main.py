"""FastAPI application entry point for Twenty AI Backend."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api.router import api_router

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception:
        pass
    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass
    yield
    try:
        from app.jobs.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="Twenty AI Sales Assistant",
    description="AI-powered sales assistant backend for Twenty CRM",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)

# Static web UI
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


@app.get("/")
async def root():
    return {
        "name": "Twenty AI Sales Assistant",
        "version": "0.1.0",
        "web_ui": "/app",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
