from unittest.mock import AsyncMock

import pytest

from app.models.schemas import NewsArticle
from app.services.news_service import _select_sources_for_fetch, fetch_news
from app.utils.feed_config import ISRAELI_SOURCES_FEEDS, INTERNATIONAL_SOURCES_FEEDS


def test_international_category_prefers_international_sources():
    source_map = {}
    source_map.update(ISRAELI_SOURCES_FEEDS)
    source_map.update(INTERNATIONAL_SOURCES_FEEDS)

    selected = _select_sources_for_fetch(source_map, category="international", language="english", max_sources=12)

    selected_names = [name for name, _ in selected]
    international_names = [name for name in selected_names if name in INTERNATIONAL_SOURCES_FEEDS]
    israeli_names = [name for name in selected_names if name in ISRAELI_SOURCES_FEEDS]

    assert international_names, "international category should include international sources"
    assert len(international_names) >= len(israeli_names), "international category should prefer international sources over Israeli ones"


def test_positive_topic_includes_israeli_positive_query_feeds():
    from app.utils.feed_config import TOPIC_MIXED_FEEDS

    positive_feeds = TOPIC_MIXED_FEEDS.get("positive", {})
    assert "Google News IL Positive Hebrew" in positive_feeds
    assert "Google News IL Positive Innovation" in positive_feeds
    assert "&hl=he-il" in positive_feeds["Google News IL Positive Hebrew"].lower()


def test_positive_topic_blocks_war_related_imagery_articles():
    from app.utils.filters import is_topic_relevant

    title = "Israeli startup wins award after recovery from attack"
    description = "A team announced a breakthrough despite recent missile strikes."
    assert not is_topic_relevant("positive", title, description, source_name="Times of Israel", source_url="https://www.timesofisrael.com")


@pytest.mark.asyncio
async def test_fetch_news_positive_applies_positive_filters(monkeypatch):
    # Patch the RSS feed fetcher so no network call is required.
    fake_article = NewsArticle(
        title="Israeli project wins award after breakthrough",
        source_type=None,
        link="https://example.com/article1",
        description="A major discovery that inspired hope in the community.",
        pub_date="2026-07-01T00:00:00Z",
        source="Times of Israel",
        source_url="https://www.timesofisrael.com",
        image_url=None,
        guid="test-guid-1",
    )

    async def fake_fetch_single_feed(url, source_name, limit):
        return [fake_article]

    monkeypatch.setattr("app.services.news_service._fetch_single_feed", fake_fetch_single_feed)
    monkeypatch.setattr("app.services.news_service.enrich_images", AsyncMock(return_value=[fake_article]))

    response = await fetch_news(
        category="positive",
        limit=1,
        exclude_negative=True,
        use_cache=False,
        with_analysis=False,
        language="hebrew",
        user_tier="free",
    )

    assert response.total == 1
    assert len(response.articles) == 1
    assert response.articles[0].source_type == "israel"
    assert "breakthrough" in response.articles[0].title.lower()
