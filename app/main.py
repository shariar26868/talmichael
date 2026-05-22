# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from app.Api.google_news import router as news_router
from app.Api.social_media import router as social_media_router

app = FastAPI(
    title="Israel News API",
    description="Aggregates news from verified Israeli outlets across multiple categories.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(news_router)
app.include_router(social_media_router)



@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Israel News API is running", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}
