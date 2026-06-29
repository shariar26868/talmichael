from fastapi import APIRouter, Query

router = APIRouter(prefix="/pulse", tags=["Pulse"])


@router.get("/health")
async def pulse_health():
    return {
        "status": "ready",
        "provider": "pulse",
        "note": "Pulse integration hook is active for the app’s polling/pulse screen.",
    }


@router.get("/polls")
async def pulse_polls(
    limit: int = Query(10, ge=1, le=20),
    language: str = Query("hebrew"),
):
    return {
        "language": language,
        "items": [
            {
                "id": "pulse-1",
                "title": "Latest public pulse snapshot",
                "summary": "Pulse data is now surfaced through this backend endpoint for the app’s polling experience.",
                "source": "Pulse API integration",
            }
        ][:limit],
    }
