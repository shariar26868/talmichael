# app/routes/youtube.py
"""
YouTube Podcast Search API.

POST /youtube/podcasts          — search by prompt, get podcast video links
GET  /youtube/podcasts          — same via query param (for quick browser testing)
GET  /youtube/podcasts/{video_id} — single video detail / embed info
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.youtube_service import search_podcasts

router = APIRouter(prefix="/youtube", tags=["YouTube Podcasts"])


# ── Request / Response schemas ────────────────────────────────────────────────

class PodcastSearchRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Topic or query to search for (e.g. 'Israeli politics', 'Gaza ceasefire debate')",
        examples=["Israeli elections 2026", "Netanyahu podcast interview"],
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Maximum number of podcast videos to return (1–25)",
    )
    language: str = Field(
        default="en",
        description="Preferred result language code (en, he, ar, etc.)",
        examples=["en", "he"],
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/podcasts",
    summary="Search YouTube for podcast videos by topic",
    description=(
        "Given a prompt/topic, returns a list of YouTube podcast-style videos "
        "matching that topic. Results are filtered to long-form content (>10 minutes). "
        "Each result includes: title, channel, duration, thumbnail, and YouTube URL. "
        "Works without a YouTube API key (falls back to HTML scraping). "
        "For richer metadata (view counts, descriptions), add YOUTUBE_API_KEY to .env."
    ),
    response_description="List of YouTube podcast video results",
)
async def search_podcasts_post(request: PodcastSearchRequest):
    """Search YouTube for podcast-length videos matching the given prompt."""
    result = await search_podcasts(
        prompt=request.prompt,
        max_results=request.max_results,
        language=request.language,
    )
    if not result["results"]:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"No podcast videos found for: '{request.prompt}'",
                "suggestion": "Try a broader topic or different keywords.",
                "api_key_configured": result.get("api_key_configured", False),
            },
        )
    return result


@router.get(
    "/podcasts",
    summary="Search YouTube podcasts via query param (GET version)",
    description=(
        "GET version of the podcast search — useful for quick browser testing. "
        "Pass the topic via ?prompt=... and get YouTube podcast links back."
    ),
)
async def search_podcasts_get(
    prompt: str = Query(
        ...,
        min_length=2,
        max_length=300,
        description="Topic to search for",
        examples=["Israeli elections 2026"],
    ),
    max_results: int = Query(
        default=10,
        ge=1,
        le=25,
        description="Max results (1–25)",
    ),
    language: str = Query(
        default="en",
        description="Preferred language code",
    ),
):
    """Search YouTube podcasts via GET — for browser/quick testing."""
    result = await search_podcasts(
        prompt=prompt,
        max_results=max_results,
        language=language,
    )
    if not result["results"]:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"No podcast videos found for: '{prompt}'",
                "suggestion": "Try a broader topic or different keywords.",
            },
        )
    return result


@router.get(
    "/podcasts/{video_id}",
    summary="Get embed info for a specific YouTube video",
    description=(
        "Returns embed-ready data for a specific YouTube video by its video ID. "
        "Useful for opening or embedding a video in the frontend."
    ),
)
async def get_video_embed(video_id: str):
    """Get embed URL and thumbnail for a specific YouTube video ID."""
    if not video_id or len(video_id) != 11:
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID (must be 11 characters)")
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
        "thumbnail_default": f"https://i.ytimg.com/vi/{video_id}/default.jpg",
        "thumbnail_hq": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "thumbnail_maxres": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
    }
