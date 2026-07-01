from app.models.schemas import NewsArticle
from app.routes.social_media import build_social_query


def test_build_social_query_uses_title_and_source_context():
    article = NewsArticle(
        title="Israeli elections 2026 spark debate",
        link="https://example.com/news/1",
        description="A new article about the election race.",
        pub_date="2026-07-01T00:00:00Z",
        source="The Times of Israel",
        source_url="https://www.timesofisrael.com",
    )

    query = build_social_query(article)

    assert "Israeli elections 2026" in query
    assert "The Times of Israel" in query or "timesofisrael" in query.lower()
    assert "lang:en" in query
