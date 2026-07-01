import pytest
from datetime import datetime

from app.routes.social_media import _build_query, _ensure_twscrape_active


class DummyPool:
    async def stats(self):
        return {"total": 0, "active": 0, "inactive": 0}


class DummyAPI:
    def __init__(self):
        self.pool = DummyPool()


class ActiveDummyPool(DummyPool):
    async def stats(self):
        return {"total": 1, "active": 1, "inactive": 0}


class ActiveDummyAPI(DummyAPI):
    def __init__(self):
        self.pool = ActiveDummyPool()


@pytest.mark.asyncio
async def test_ensure_twscrape_active_raises_if_no_active_accounts():
    api = DummyAPI()

    with pytest.raises(Exception) as exc_info:
        await _ensure_twscrape_active(api)

    assert "no active twitter accounts" in str(exc_info.value).lower()


def test_build_query_with_israeli_only_adds_accounts_and_hashtags():
    query = _build_query("israel news", israeli_only=True)
    assert "from:Jerusalem_Post" in query
    assert "#Israel" in query
    assert "lang:en" in query


class DummySearchAPI(ActiveDummyAPI):
    def __init__(self):
        super().__init__()
        self._tweets = [
            type("Tweet", (), {
                "user": type("U", (), {"username": "testuser"})(),
                "date": datetime.utcnow(),
                "rawContent": "test tweet",
                "id": 1,
            }),
        ]

    async def search(self, query, limit=10):
        for tweet in self._tweets[:limit]:
            yield tweet


@pytest.mark.asyncio
async def test_search_all_twitter_returns_default_news_query(monkeypatch):
    from app.routes.social_media import search_all_twitter

    api = DummySearchAPI()
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routes.social_media._TWSCRAPE_AVAILABLE", True)
    monkeypatch.setattr("app.routes.social_media._get_tw_api", lambda: api)
    monkeypatch.setattr("app.routes.social_media._ensure_twscrape_active", noop)

    result = await search_all_twitter(limit=1, israeli_only=True)

    assert result["query"] == "news israel"
    assert "from:Jerusalem_Post" in result["full_query"]
    assert result["count"] == 1
    assert result["tweets"][0].title == "Tweet by @testuser"


@pytest.mark.asyncio
async def test_social_and_news_combined_returns_news_and_social(monkeypatch):
    from app.routes.social_media import social_and_news

    api = DummySearchAPI()
    async def noop(*args, **kwargs):
        return None

    async def fake_fetch_all_news(limit, user_tier, with_analysis):
        return {
            "meta": {"title": "Combined News"},
            "total": 1,
            "articles": [{"title": "sample news"}],
        }

    monkeypatch.setattr("app.routes.social_media._TWSCRAPE_AVAILABLE", True)
    monkeypatch.setattr("app.routes.social_media._get_tw_api", lambda: api)
    monkeypatch.setattr("app.routes.social_media._ensure_twscrape_active", noop)
    monkeypatch.setattr(
        "app.services.news_service.fetch_all_news",
        fake_fetch_all_news,
    )

    result = await social_and_news(
        limit=1,
        israeli_only=True,
        include_news=True,
        include_social=True,
    )

    assert "news" in result
    assert "social" in result
    assert result["news"]["meta"]["title"] == "Combined News"
    assert result["social"]["query"] == "news israel"


@pytest.mark.asyncio
async def test_social_and_news_returns_news_when_social_down(monkeypatch):
    from fastapi import HTTPException
    from app.routes.social_media import social_and_news

    api = DummySearchAPI()

    async def noop(*args, **kwargs):
        return None

    async def fake_social(*args, **kwargs):
        raise HTTPException(
            status_code=503,
            detail="twscrape has no active Twitter accounts.",
        )

    async def fake_fetch_all_news(limit, user_tier, with_analysis):
        return {
            "meta": {"title": "Combined News"},
            "total": 1,
            "articles": [{"title": "sample news"}],
        }

    monkeypatch.setattr("app.routes.social_media._TWSCRAPE_AVAILABLE", True)
    monkeypatch.setattr("app.routes.social_media._get_tw_api", lambda: api)
    monkeypatch.setattr("app.routes.social_media._ensure_twscrape_active", noop)
    monkeypatch.setattr("app.routes.social_media._search_all_social", fake_social)
    monkeypatch.setattr(
        "app.services.news_service.fetch_all_news",
        fake_fetch_all_news,
    )

    result = await social_and_news(
        limit=1,
        israeli_only=True,
        include_news=True,
        include_social=True,
    )

    assert result["news"]["meta"]["title"] == "Combined News"
    assert result["social"] == []
    assert "social_error" in result
    assert "twscrape has no active Twitter accounts" in result["social_error"]
