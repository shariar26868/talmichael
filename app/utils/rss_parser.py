# app/utils/rss_parser.py
"""RSS XML parsing utilities."""

import xml.etree.ElementTree as ET
from datetime import datetime

from app.models.schemas import FeedMeta, NewsArticle, NewsResponse


def parse_rss(xml_text: str, limit: int) -> NewsResponse:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Invalid RSS feed structure")

    meta = FeedMeta(
        title=channel.findtext("title", ""),
        description=channel.findtext("description", ""),
        link=channel.findtext("link", ""),
        last_build_date=channel.findtext("lastBuildDate", ""),
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )

    articles = []
    for item in channel.findall("item")[:limit]:
        title = item.findtext("title", "")
        description = item.findtext("description", "") or ""

        source_el  = item.find("source")
        source_name = source_el.text if source_el is not None else None
        source_url  = source_el.get("url") if source_el is not None else None

        pub_date_raw = item.findtext("pubDate", "")
        try:
            pub_date = datetime.strptime(pub_date_raw, "%a, %d %b %Y %H:%M:%S %Z").isoformat() + "Z"
        except Exception:
            pub_date = pub_date_raw

        articles.append(NewsArticle(
            title=title,
            link=item.findtext("link", ""),
            description=description,
            pub_date=pub_date,
            source=source_name,
            source_url=source_url,
            guid=item.findtext("guid", ""),
        ))

    return NewsResponse(meta=meta, total=len(articles), articles=articles)
