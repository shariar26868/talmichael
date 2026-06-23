# app/utils/rss_parser.py
"""RSS XML parsing utilities."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime

from app.models.schemas import FeedMeta, NewsArticle, NewsResponse


def _find_media_element(item, tag_name):
    # Support common media namespaces like media:content and media:thumbnail.
    ns_tag = f"{{http://search.yahoo.com/mrss/}}{tag_name}"
    return item.find(tag_name) or item.find(ns_tag)


def _extract_image_url(item, description: str | None) -> str | None:
    # enclosure tag is the most common image container in RSS.
    enclosure = item.find("enclosure")
    if enclosure is not None and enclosure.get("url"):
        return enclosure.get("url")

    media_content = _find_media_element(item, "content")
    if media_content is not None and media_content.get("url"):
        return media_content.get("url")

    media_thumbnail = _find_media_element(item, "thumbnail")
    if media_thumbnail is not None and media_thumbnail.get("url"):
        return media_thumbnail.get("url")

    if description:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _clean_xml_text(xml_text: str) -> str:
    # Remove invalid XML control characters that often break malformed feeds.
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", xml_text)


def parse_rss(xml_data: bytes | str, limit: int) -> NewsResponse:
    if isinstance(xml_data, bytes):
        try:
            xml_text = xml_data.decode("utf-8", errors="replace")
        except Exception:
            xml_text = str(xml_data)
    else:
        xml_text = xml_data

    try:
        # Pymongo/ElementTree parses bytes better when it has encoding in header,
        # but if we pass a string, let's encode it to utf-8 bytes
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        clean_text = _clean_xml_text(xml_text)
        root = ET.fromstring(clean_text.encode("utf-8"))
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

        image_url = _extract_image_url(item, description)

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
            image_url=image_url,
            guid=item.findtext("guid", ""),
        ))

    return NewsResponse(meta=meta, total=len(articles), articles=articles)

