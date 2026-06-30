import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.models.schemas import FramingAnalysis, VerifiedClaim
from app.services.fact_check_service import (
    analyze_framing,
    analyze_and_store_article,
    compute_verification_confidence,
    extract_verifiable_claims,
)


def test_extract_verifiable_claims_detects_numbers_quotes_and_stats():
    title = "New report: 45% of citizens support the law"
    description = (
        'A recent study found that "the majority of respondents agree" and data shows the law passed with 60% support.'
    )

    claims = extract_verifiable_claims(title, description)

    assert len(claims) >= 1
    assert any("45%" in claim or "60%" in claim for claim in claims)
    assert any("the majority of respondents agree" in claim for claim in claims)


def test_extract_verifiable_claims_matches_percent_values():
    title = "Price jump 10% expected"
    description = "The report says 10% of voters prefer the new policy."

    claims = extract_verifiable_claims(title, description)

    assert any("10%" in claim for claim in claims)


def test_analyze_framing_detects_perspective_balance_and_omission_signals():
    title = "Breaking: Government says the plan will save lives"
    description = (
        "The minister said the initiative is critical, however critics say it is too expensive. "
        "Experts confirmed the figures are solid."
    )

    framing = analyze_framing(title, description)

    assert framing.perspective_balance in {"balanced", "multi-perspective"}
    assert framing.attribution_count >= 2
    assert "no opposing viewpoint cited" not in framing.omission_signals


def test_compute_verification_confidence_aggregates_signals():
    claims = [
        VerifiedClaim(
            claim_text="The budget increase was 20%.",
            verification_status="partially_verified",
            evidence_sources=["Source A"],
            confidence=0.8,
            explanation="Found matching figures in other coverage.",
        )
    ]

    framing = FramingAnalysis(
        headline_body_consistency=0.8,
        attribution_count=3,
        perspective_balance="balanced",
        narrative_frame="economic",
        voice_analysis="active",
        omission_signals=[],
    )

    confidence = asyncio.run(
        compute_verification_confidence(
            article_guid="test-guid",
            source_credibility=0.8,
            claims=claims,
            framing=framing,
            cross_source={"agreement_score": 0.75},
            external_evidence=[{"claim_text": "Test", "rating": "true"}],
            user_vote_credibility=0.6,
        )
    )

    assert 0.7 <= confidence.overall_score <= 0.9
    assert confidence.label in {"verified", "highly_verified"}
    assert confidence.components["source_credibility"] == 0.8
    assert confidence.components["cross_source_agreement"] == 0.75
    assert confidence.components["external_fact_check"] >= 0.4


def test_analyze_and_store_article_persists_results(monkeypatch):
    fake_db = MagicMock()
    fake_db.cross_source_matches.find_one = AsyncMock(return_value=None)
    fake_db.source_credibility.find_one = AsyncMock(return_value=None)
    fake_aggregate_result = MagicMock()
    fake_aggregate_result.to_list = AsyncMock(return_value=[])
    fake_db.credibility_votes.aggregate = MagicMock(return_value=fake_aggregate_result)
    fake_db.verified_claims.insert_many = AsyncMock()
    fake_db.framing_analyses.update_one = AsyncMock()
    fake_db.analysis_audit_log.insert_one = AsyncMock()
    fake_cursor = MagicMock()
    fake_cursor.to_list = AsyncMock(return_value=[])
    fake_db.cached_articles.find = MagicMock(return_value=fake_cursor)
    fake_db.cached_articles.update_one = AsyncMock()

    monkeypatch.setattr("app.services.fact_check_service.get_db", lambda: fake_db)
    monkeypatch.setattr("app.services.fact_check_service.check_google_factcheck", AsyncMock(return_value=[]))
    monkeypatch.setattr("app.core.cache.cache_delete_pattern", AsyncMock())
    monkeypatch.setattr("app.services.ai_service.SOURCE_CREDIBILITY_SEED", {"Test Source": 0.9})

    article = {
        "guid": "test-guid",
        "title": "Test title 10%",
        "description": 'A quick quote "hello" and a statistic 10% in the description.',
        "source": "Test Source",
    }

    result = asyncio.run(analyze_and_store_article(article))

    assert result.overall_score >= 0.0
    fake_db.cached_articles.update_one.assert_called_once()
    fake_db.analysis_audit_log.insert_one.assert_called_once()
    fake_db.framing_analyses.update_one.assert_called_once()
    fake_db.verified_claims.insert_many.assert_called_once()
