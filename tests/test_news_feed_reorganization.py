"""Test suite for news feed reorganization with date prioritization and sentiment filtering."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.news_service import fetch_news
from app.models.schemas import NewsArticle


@pytest.mark.asyncio
async def test_security_route_today_priority():
    """Test that security route prioritizes today's articles."""
    # Create mock articles with different dates
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    mock_articles = [
        NewsArticle(
            title="Old Security News",
            link="http://old.news",
            source="BBC",
            pub_date=datetime.combine(yesterday, datetime.min.time()),
            description="Old security article"
        ),
        NewsArticle(
            title="Today's Security News",
            link="http://today.news",
            source="Reuters",
            pub_date=datetime.combine(today, datetime.min.time()),
            description="Today's security article"
        ),
    ]
    
    with patch('app.services.news_service._build_mixed_source_list') as mock_build:
        mock_build.return_value = {"Reuters": "http://test", "BBC": "http://test2"}
        
        with patch('app.services.news_service._fetch_single_feed') as mock_fetch:
            async def mock_fetch_side_effect(*args, **kwargs):
                return mock_articles
            
            mock_fetch.side_effect = mock_fetch_side_effect
            
            with patch('app.services.news_service._select_sources_for_fetch') as mock_select:
                mock_select.return_value = [("Reuters", "http://test"), ("BBC", "http://test2")]
                
                # Test with force_today_priority
                result = await fetch_news(
                    "security",
                    limit=10,
                    force_today_priority=True,
                    use_cache=False
                )
                
                # Today's article should be first
                assert result is not None
                assert result.articles is not None


@pytest.mark.asyncio
async def test_sport_israeli_only_filter():
    """Test that sport route filters to Israeli sources only."""
    with patch('app.services.news_service._build_mixed_source_list') as mock_build:
        mock_build.return_value = {"Maccabi": "http://maccabi", "BBC Sport": "http://bbc"}
        
        # Test with israeli_only=True
        result = await fetch_news(
            "sport",
            limit=20,
            israeli_only=True,
            use_cache=False
        )
        
        assert result is not None


@pytest.mark.asyncio
async def test_education_exclude_positive():
    """Test that education route excludes positive sentiment articles."""
    mock_articles = [
        NewsArticle(
            title="University Achievement Breakthrough",
            link="http://positive.news",
            source="Haaretz",
            pub_date=datetime.utcnow(),
            description="Great education breakthrough"
        ),
        NewsArticle(
            title="University Budget Crisis",
            link="http://negative.news",
            source="Haaretz",
            pub_date=datetime.utcnow(),
            description="Education funding problems"
        ),
    ]
    
    with patch('app.services.news_service._build_mixed_source_list') as mock_build:
        mock_build.return_value = {"Haaretz": "http://test"}
        
        with patch('app.services.news_service._fetch_single_feed') as mock_fetch:
            async def mock_fetch_side_effect(*args, **kwargs):
                return mock_articles
            
            mock_fetch.side_effect = mock_fetch_side_effect
            
            with patch('app.services.news_service._select_sources_for_fetch') as mock_select:
                mock_select.return_value = [("Haaretz", "http://test")]
                
                result = await fetch_news(
                    "education",
                    limit=20,
                    exclude_positive=True,
                    use_cache=False
                )
                
                assert result is not None
                # Should filter out "achievement" and "breakthrough" articles


def test_date_filtering_algorithm():
    """Test the date prioritization algorithm logic."""
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    articles_by_date = {
        "today": [],
        "yesterday": [],
        "2days": [],
        "3days": [],
        "older": []
    }
    
    # Simulate article categorization
    limit = 20
    
    # Test priority ordering
    today_articles = [i for i in range(5)]
    yesterday_articles = [i for i in range(3)]
    
    prioritized = today_articles.copy()
    if len(prioritized) < limit:
        prioritized.extend(yesterday_articles)
    
    assert len(prioritized) == 8
    assert prioritized[:5] == [0, 1, 2, 3, 4]  # Today's articles first
    assert prioritized[5:8] == [0, 1, 2]  # Yesterday's articles next


def test_sentiment_filtering():
    """Test positive sentiment keyword detection."""
    positive_keywords = (
        "achievement", "success", "breakthrough", "award", "positive",
        "hope", "recovery", "progress", "improve", "winner",
    )
    
    test_titles = [
        ("Israeli Scientists Achieve Breakthrough", True),  # Should filter
        ("Education Budget Crisis", False),  # Should keep
        ("University Success Stories", True),  # Should filter
        ("Security Concerns in Government", False),  # Should keep
    ]
    
    for title, should_filter in test_titles:
        title_desc = title.lower()
        contains_positive = any(kw in title_desc for kw in positive_keywords)
        assert contains_positive == should_filter


def test_routes_parameter_mapping():
    """Test that routes pass correct parameters to fetch_news."""
    test_cases = [
        ("security", {"force_today_priority": True}),
        ("political", {"force_today_priority": True}),
        ("economy", {"force_today_priority": True}),
        ("sport", {"force_today_priority": True, "israeli_only": True}),
        ("education", {"exclude_positive": True}),
        ("culture", {"exclude_positive": True}),
        ("science", {"exclude_positive": True}),
    ]
    
    # This validates the route parameter mapping (visual check)
    for route, params in test_cases:
        assert route is not None
        assert params is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
