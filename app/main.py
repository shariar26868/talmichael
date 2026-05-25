# app/main.py

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db, close_db
from app.routes.news import router as news_router
from app.routes.ai import router as ai_router
from app.routes.social_media import router as social_router
from app.routes.political import router as political_router
from app.routes.correlation import router as correlation_router
from app.routes.insights import router as insights_router
from app.routes.qa import router as qa_router


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(ai_router)
app.include_router(social_router)
app.include_router(political_router)
app.include_router(correlation_router)
app.include_router(insights_router)
app.include_router(qa_router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "version": "3.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}
