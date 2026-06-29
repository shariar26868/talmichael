# app/main.py

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db, close_db
from app.routes.news import router as news_router
from app.routes.ai import router as ai_router
from app.routes.social_media import router as social_router
from app.routes.political import router as political_router
from app.routes.correlation import router as correlation_router
from app.routes.insights import router as insights_router
from app.routes.qa import router as qa_router
from app.routes.health import router as health_router
from app.routes.bills import router as bills_router
from app.routes.statistics import router as statistics_router
from app.routes.summary import router as summary_router
# ── New routes (Phase 4 — UI-driven features) ────────────────────────────────
from app.routes.blocs import router as blocs_router
from app.routes.politics101 import router as politics101_router
from app.routes.election_voting import router as election_voting_router
from app.routes.pulse import router as pulse_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Israel News & Political Intelligence API",
    description=(
        "Real-time Israeli news aggregation with AI-powered bias detection, "
        "sentiment analysis, Knesset intelligence, and political tracking."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(ai_router)
app.include_router(social_router)
# Phase 4 — UI-driven features (specifically blocs_router needs to be registered before political_router to avoid clashing on GET /political/parties/{party_id})
app.include_router(blocs_router)
app.include_router(political_router)
app.include_router(correlation_router)
app.include_router(insights_router)
app.include_router(qa_router)
app.include_router(health_router)
app.include_router(bills_router)
app.include_router(statistics_router)
app.include_router(summary_router)
app.include_router(politics101_router)
app.include_router(election_voting_router)
app.include_router(pulse_router)




@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "version": "3.0.0",
        "docs": "/docs",
        "default_language": "hebrew",
        "logo_url": "/static/logo.svg",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}
