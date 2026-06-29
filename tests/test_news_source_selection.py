from app.services.news_service import _select_sources_for_fetch
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
