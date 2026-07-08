import asyncio

import pytest

from app.services import election_voting_service


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return list(self.docs)


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, *args, **kwargs):
        return FakeCursor(self.docs)


class FakeDB:
    def __init__(self, docs=None):
        self.cached_articles = FakeCollection(docs or [])
        self.mps = FakeCollection([])
        self.parties = FakeCollection([])
        self.election_party_votes = FakeCollection([])
        self.election_candidate_votes = FakeCollection([])


def test_get_election_news_fetches_live_articles_when_cache_is_empty(monkeypatch):
    db = FakeDB([])
    monkeypatch.setattr(election_voting_service, "get_db", lambda: db)

    async def fake_fetch_news(*args, **kwargs):
        class FakeArticle:
            def __init__(self, title, description, link, source):
                self.title = title
                self.description = description
                self.link = link
                self.source = source
                self.image_url = None
                self.guid = link

            def model_dump(self, exclude_none=True):
                return {
                    "title": self.title,
                    "description": self.description,
                    "link": self.link,
                    "source": self.source,
                    "image_url": self.image_url,
                    "guid": self.guid,
                }

        class FakeNews:
            def __init__(self, articles):
                self.total = len(articles)
                self.articles = articles

        return FakeNews([
            FakeArticle("Election article", "Live election coverage", "https://example.com/election", "Reuters"),
        ])

    monkeypatch.setattr(election_voting_service, "fetch_news", fake_fetch_news, raising=False)

    result = asyncio.run(election_voting_service.get_election_news(limit=3))

    assert result["total"] >= 1
    assert any(article["title"] == "Election article" for article in result["articles"])


def test_get_election_participants_includes_party_websites(monkeypatch):
    db = FakeDB([])
    monkeypatch.setattr(election_voting_service, "get_db", lambda: db)

    result = asyncio.run(election_voting_service.get_election_participants())
    party_entry = next(item for item in result["participants"] if item["type"] == "party")

    assert party_entry["official_website"]
    assert party_entry["website"] == party_entry["official_website"]
