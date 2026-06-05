"""Health check and diagnostics endpoints."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/diagnostic", tags=["Health & Diagnostics"])


@router.get("/status")
async def health_status():
    """Overall API health status."""
    return {
        "status": "ok",
        "services": {
            "openai": "configured" if settings.openai_api_key else "not configured",
            "gemini": "configured" if settings.gemini_api_key else "not configured",
            "claude": "configured" if settings.claude_api_key else "not configured",
            "perplexity": "configured" if settings.perplexity_api_key else "not configured",
            "mongodb": "check via /political/mps or similar endpoint",
        },
    }


@router.get("/openai/test")
async def test_openai():
    """Test OpenAI API connectivity and key validity.
    WARNING: Makes a real API call (uses ~50 tokens)."""
    if not settings.openai_api_key:
        return {
            "status": "error",
            "message": "OPENAI_API_KEY not set in .env",
        }

    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=5.0)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'ok'"}],
            temperature=0.1,
            max_tokens=5,
        )
        
        return {
            "status": "ok",
            "message": "OpenAI API is reachable and key is valid",
            "model": response.model,
            "tokens_used": response.usage.total_tokens,
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": "OpenAI API test failed. Key may be expired, revoked, or invalid.",
            "error": error_msg[:200],
            "solution": "Get a new API key from https://platform.openai.com/account/api-keys or check your OpenAI account billing/status",
        }


@router.get("/gemini/test")
async def test_gemini():
    """Test Gemini API connectivity and key validity."""
    if not settings.gemini_api_key:
        return {
            "status": "not_configured",
            "message": "GEMINI_API_KEY not set in .env",
        }

    try:
        import google.generativeai as genai
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-pro")
        
        response = model.generate_content("Say 'ok'")
        
        return {
            "status": "ok",
            "message": "Gemini API is reachable and key is valid",
            "response": response.text[:100],
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": "Gemini API test failed. Key may be invalid or API unavailable.",
            "error": error_msg[:200],
            "solution": "Get a Gemini API key from https://aistudio.google.com/app/apikey",
        }
