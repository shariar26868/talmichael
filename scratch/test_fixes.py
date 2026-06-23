"""
Test the two fixes:
1. source_type fix — Hebrew-named Israeli sources now classified correctly
2. image enricher — Google News RSS articles now get OG images

Run: python scratch/test_fixes.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import NewsArticle
from app.utils.filters import is_israeli_source
from app.utils.image_enricher import enrich_images


def test_source_classification():
    print("\n" + "="*60)
    print("TEST 1: source_type classification")
    print("="*60)

    cases = [
        # (source_name, source_url, expected)
        ("הארץ",             "https://www.haaretz.co.il",      True),
        ("היום",             "https://www.israelhayom.co.il",  True),
        ("כאן 11",           "https://www.kan.org.il",         True),
        ("mako",             "https://www.mako.co.il",         True),
        ("www.israelhayom.com", "https://www.israelhayom.com", True),
        ("Ynetnews",         "https://www.ynetnews.com",       True),
        ("Times of Israel",  "https://www.timesofisrael.com",  True),
        ("Al Jazeera English","https://www.aljazeera.com",     False),
        ("BBC Arabic",       "https://www.bbc.com/arabic",     False),
        ("Sky News Arabia",  "https://www.skynewsarabia.com",  False),
    ]

    all_pass = True
    for name, url, expected in cases:
        result = is_israeli_source(name, url)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            all_pass = False
        print(f"  {status} [{name}] -> {'israel' if result else 'global'} (expected {'israel' if expected else 'global'})")

    print(f"\n  {'All passed' if all_pass else 'FAILURES detected'}")


async def test_google_news_images():
    print("\n" + "="*60)
    print("TEST 2: Google News RSS image enrichment")
    print("="*60)

    # Article with Google News RSS link (הארץ via Google News)
    articles = [
        NewsArticle(
            title='ראש שב"כ מתריע בדיונים סגורים: 7 באוקטובר הבא יהיה באילת - הארץ',
            link="https://news.google.com/rss/articles/CBMiqwFBVV95cUxPc0ljd0lQVUh2aklkUkV2dGUyZFh0WURCbTZjazBoNTl3YjV4M3N1ZmpXbGlick1Eb1o2RXNRV1Vqa0NEM2d0WGx0ekpJMnJsUGdHZmlXT0cxakFaUkFEUWNURWxVMTNFXzhNQzFKQXlsS1JlY2tVY1NDZmRrZTZ3cHVvckFHcU5DYV9RQVRZT3RzMVhCVDZKYzQ3bTVLaHhMLUVPUDVsdnduVFE?oc=5",
            description='<a href="https://news.google.com/rss/articles/CBMiqwFBVV95cUxPc0ljd0lQVUh2aklkUkV2dGUyZFh0WURCbTZjazBoNTl3YjV4M3N1ZmpXbGlick1Eb1o2RXNRV1Vqa0NEM2d0WGx0ekpJMnJsUGdHZmlXT0cxakFaUkFEUWNURWxVMTNFXzhNQzFKQXlsS1JlY2tVY1NDZmRrZTZ3cHVvckFHcU5DYV9RQVRZT3RzMVhCVDZKYzQ3bTVLaHhMLUVPUDVsdnduVFE?oc=5" target="_blank">ראש שב"כ מתריע</a>&nbsp;&nbsp;<font color="#6f6f6f">הארץ</font>',
            pub_date="2026-06-22T10:37:00Z",
            source="הארץ",
            source_url="https://www.haaretz.co.il",
            image_url=None,
        ),
        NewsArticle(
            title='Trump: If Iran doesn\'t abide by deal, \'I will do what I have to do\'',
            link="https://www.timesofisrael.com/trump-if-iran-doesnt-abide-by-deal-i-will-do-what-i-have-to-do-to-prevent-nuke/",
            description='<figure><img src="https://static-cdn.toi-media.com/www/uploads/2026/06/AP26173738399121-1024x640.jpg"></figure>',
            pub_date="Tue, 23 Jun 2026 05:24:22 +0000",
            source="Times of Israel",
            source_url="https://www.timesofisrael.com",
            image_url="https://static-cdn.toi-media.com/www/uploads/2026/06/AP26173738399121-1024x640.jpg",  # already has image
        ),
    ]

    print("\nBEFORE enrichment:")
    for a in articles:
        print(f"  [{a.source}] image_url = {a.image_url}")

    enriched = await enrich_images(articles)

    print("\nAFTER enrichment:")
    for a in enriched:
        print(f"  [{a.source}] image_url = {a.image_url}")


async def main():
    test_source_classification()
    await test_google_news_images()


if __name__ == "__main__":
    asyncio.run(main())
