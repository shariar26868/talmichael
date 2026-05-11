# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.Api.google_news import router as news_router  # ← import the router

app = FastAPI(
    title="World News API",
    description="Fetches and structures world news from Google News RSS Feed",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health routes stay on main app
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "World News API is running", "version": "1.0.0"}

@app.get("/health", tags=["Health"])
async def health():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

app.include_router(news_router)  # ← registers all /news, /categories, /search routes