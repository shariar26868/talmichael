"""
Test OG image enrichment on real articles from the Arabic feed.
Run from the project root:
    python scratch/test_image_enricher.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import NewsArticle
from app.utils.image_enricher import enrich_images


async def main():
    # Simulate articles that come back with image_url=None (Al Jazeera, Middle East Eye)
    articles = [
        NewsArticle(
            title="Algeria come from behind to win 2-1, knock Jordan out of World Cup",
            link="https://www.aljazeera.com/sports/2026/6/23/algeria-jordan-score-fifa-world-cup-2026-mahrez-gouiri-benbouali-alrashdan",
            description="Goals from Nadhir Benbouali and Amine Gouiri steered Algeria to a 2-1 win.",
            pub_date="Tue, 23 Jun 2026 05:13:18 +0000",
            source="Al Jazeera English",
            image_url=None,
        ),
        NewsArticle(
            title="Video: Israeli strike in Gaza City kills Palestinian student",
            link="https://www.middleeasteye.net/live-blog/live-blog-update/video-israeli-strike-gaza-city-kills-palestinian-student",
            description="Israeli forces struck a vehicle in Gaza City.",
            pub_date="Tue, 23 Jun 2026 06:11:45 +0100",
            source="Middle East Eye",
            image_url=None,
        ),
        # BBC Arabic — already has an image, should NOT be re-fetched
        NewsArticle(
            title="ترامب يحث إيران على شراء غذاء ودواء أمريكي",
            link="https://www.bbc.com/arabic/articles/cpd3jyzy987o",
            description="الرئيس الأمريكي يشدد على ضرورة التزام إيران.",
            pub_date="2026-06-23T00:26:18Z",
            source="BBC Arabic",
            image_url="https://ichef.bbci.co.uk/ace/ws/240/cpsprodpb/e064/live/existing_image.jpg",  # already has image
        ),
    ]

    print(f"\n{'='*60}")
    print("BEFORE enrichment:")
    for a in articles:
        print(f"  [{a.source}] image_url = {a.image_url}")

    enriched = await enrich_images(articles)

    print(f"\n{'='*60}")
    print("AFTER enrichment:")
    for a in enriched:
        print(f"  [{a.source}] image_url = {a.image_url}")

    print(f"\n{'='*60}")
    images_found = sum(1 for a in enriched if a.image_url)
    print(f"Result: {images_found}/{len(enriched)} articles have images")


if __name__ == "__main__":
    asyncio.run(main())
