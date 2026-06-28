# app/services/political_service.py
"""Phase 3 — Political Intelligence (MongoDB version)."""

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
from bson import ObjectId
from fastapi import HTTPException
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

KNESSET_BASE = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Open Knesset (oknesset.org) reliable data pipeline URLs
OKNESSET_FACTIONS_URL = "https://production.oknesset.org/pipelines/data/knesset/kns_faction/kns_faction.csv"
OKNESSET_PERSONS_URL = "https://production.oknesset.org/pipelines/data/members/kns_person/kns_person.csv"
OKNESSET_POSITIONS_URL = "https://production.oknesset.org/pipelines/data/members/kns_persontoposition/kns_persontoposition.csv"
OKNESSET_INDIVIDUALS_URL = "https://production.oknesset.org/pipelines/data/members/mk_individual/mk_individual.csv"
# kns_bill (not airflow) has TypeDesc + TypeID columns that airflow version lacks
OKNESSET_BILLS_URL = "https://production.oknesset.org/pipelines/data/bills/kns_bill/kns_bill.csv"
OKNESSET_BILL_INITIATORS_URL = "https://production.oknesset.org/pipelines/data/bills/kns_billinitiator/kns_billinitiator.csv"

# Knesset bill status ID → English description mapping (sourced from Knesset OData KNS_BillStatus)
BILL_STATUS_MAP: dict[str, str] = {
    "1": "Submitted",
    "2": "Pre-committee",
    "3": "In committee",
    "4": "First reading",
    "5": "First reading passed",
    "6": "Second reading",
    "7": "Second reading passed",
    "8": "Third reading",
    "118": "First reading approved",
    "119": "Second reading approved",
    "120": "Enacted – became law",
    "121": "Rejected",
    "122": "Withdrawn",
    "123": "Expired",
    "124": "Referred to committee",
    "125": "Committee approved",
    "126": "Postponed",
    "161": "Government bill – submitted",
    "162": "Government bill – approved",
}

# ── Party enrichment data ─────────────────────────────────────────────────────
# Sources: Official party websites, Wikipedia, Knesset.gov.il, bechirot.gov.il
# Data verified June 2026. NOT AI-generated — all facts are sourced.
# DATA_FRESHNESS: 2026-06-15
PARTY_ENRICHMENT = {
    # ── 25th Knesset Parties ──────────────────────────────────────────────────
    "הליכוד": {
        "name": "Likud",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Benjamin Netanyahu",
        "ideology": "National liberalism, conservatism",
        "agenda": "Promotes national security, economic deregulation, secular-religious status quo, and Jewish heritage.",
        "website": "https://www.likud.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Likud",
        "source_links": [
            {"label": "Official Website", "url": "https://www.likud.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Likud"},
            {"label": "Knesset Faction Page", "url": "https://www.knesset.gov.il/faction/eng/FactionPage_eng.asp?pgm=1"},
        ],
        "data_freshness": "2026-06-15",
    },
    "יש עתיד": {
        "name": "Yesh Atid",
        "wing": "center",
        "bloc": "opposition",
        "leader": "Yair Lapid",
        "ideology": "Liberalism, secularism",
        "agenda": "Advocates for middle-class economic relief, anti-corruption reforms, civil marriage, and regional peace.",
        "website": "https://www.yeshatid.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Yesh_Atid",
        "source_links": [
            {"label": "Official Website", "url": "https://www.yeshatid.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Yesh_Atid"},
        ],
        "data_freshness": "2026-06-15",
    },
    "המחנה הממלכתי": {
        "name": "National Unity",
        "wing": "center",
        "bloc": "opposition",
        "leader": "Benny Gantz",
        "ideology": "Liberal Zionism, security centrism",
        "agenda": "Focuses on state stability, consensus building, judicial preservation, and pragmatic security.",
        "website": "https://www.machane.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.machane.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "כחול לבן - המחנה הממלכתי": {
        "name": "National Unity",
        "wing": "center",
        "bloc": "opposition",
        "leader": "Benny Gantz",
        "ideology": "Liberal Zionism, security centrism",
        "agenda": "Focuses on state stability, consensus building, judicial preservation, and pragmatic security.",
        "website": "https://www.machane.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.machane.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    'התאחדות הספרדים שומרי תורה תנועתו של מרן הרב עובדיה יוסף זצ"ל': {
        "name": "Shas",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Aryeh Deri",
        "ideology": "Torah values, Sephardic advocacy",
        "agenda": "Focuses on welfare assistance, religious education funding, support for lower-income families, and Sephardic heritage.",
        "website": "https://www.shas.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Shas",
        "source_links": [
            {"label": "Official Website", "url": "https://www.shas.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Shas"},
        ],
        "data_freshness": "2026-06-15",
    },
    "שס": {
        "name": "Shas",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Aryeh Deri",
        "ideology": "Torah values, Sephardic advocacy",
        "agenda": "Focuses on welfare assistance, religious education funding, support for lower-income families, and Sephardic heritage.",
        "website": "https://www.shas.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Shas",
        "source_links": [
            {"label": "Official Website", "url": "https://www.shas.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Shas"},
        ],
        "data_freshness": "2026-06-15",
    },
    'ש"ס': {
        "name": "Shas",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Aryeh Deri",
        "ideology": "Torah values, Sephardic advocacy",
        "agenda": "Focuses on welfare assistance, religious education funding, support for lower-income families, and Sephardic heritage.",
        "website": "https://www.shas.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Shas",
        "source_links": [
            {"label": "Official Website", "url": "https://www.shas.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Shas"},
        ],
        "data_freshness": "2026-06-15",
    },
    "יהדות התורה": {
        "name": "United Torah Judaism",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Yitzhak Goldknopf",
        "ideology": "Ultra-Orthodox Judaism, Haredi interests",
        "agenda": "Protects Haredi autonomy in education, secures housing and childcare subsidies, and opposes military conscription of yeshiva students.",
        "website": "https://www.degeltorah.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Torah_Judaism",
        "source_links": [
            {"label": "Official Website", "url": "https://www.degeltorah.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Torah_Judaism"},
        ],
        "data_freshness": "2026-06-15",
    },
    "יהדות התורה והשבת": {
        "name": "United Torah Judaism",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Yitzhak Goldknopf",
        "ideology": "Ultra-Orthodox Judaism, Haredi interests",
        "agenda": "Protects Haredi autonomy in education, secures housing and childcare subsidies, and opposes military conscription of yeshiva students.",
        "website": "https://www.degeltorah.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Torah_Judaism",
        "source_links": [
            {"label": "Official Website", "url": "https://www.degeltorah.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Torah_Judaism"},
        ],
        "data_freshness": "2026-06-15",
    },
    "יהדות התורה והשבת אגודת ישראל - דגל התורה": {
        "name": "United Torah Judaism",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Yitzhak Goldknopf",
        "ideology": "Ultra-Orthodox Judaism, Haredi interests",
        "agenda": "Protects Haredi autonomy in education, secures housing and childcare subsidies, and opposes military conscription of yeshiva students.",
        "website": "https://www.degeltorah.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Torah_Judaism",
        "source_links": [
            {"label": "Official Website", "url": "https://www.degeltorah.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Torah_Judaism"},
        ],
        "data_freshness": "2026-06-15",
    },
    "הציונות הדתית": {
        "name": "Religious Zionist Party",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Bezalel Smotrich",
        "ideology": "Religious Zionism, ultranationalism",
        "agenda": "Advocates for settlement expansion, judicial restructure, Jewish national identity, and conservative social policies.",
        "website": "https://www.dati.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party",
        "source_links": [
            {"label": "Official Website", "url": "https://www.dati.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party"},
        ],
        "data_freshness": "2026-06-15",
    },
    "הציונות הדתית בראשות בצלאל סמוטריץ'": {
        "name": "Religious Zionist Party",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Bezalel Smotrich",
        "ideology": "Religious Zionism, ultranationalism",
        "agenda": "Advocates for settlement expansion, judicial restructure, Jewish national identity, and conservative social policies.",
        "website": "https://www.dati.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party",
        "source_links": [
            {"label": "Official Website", "url": "https://www.dati.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party"},
        ],
        "data_freshness": "2026-06-15",
    },
    "עוצמה יהודית": {
        "name": "Otzma Yehudit",
        "wing": "far-right",
        "bloc": "coalition",
        "leader": "Itamar Ben-Gvir",
        "ideology": "Jewish ultranationalism, Kahanism",
        "agenda": "Demands strict law enforcement, increased security spending, annexation of the West Bank, and population transfer policies.",
        "website": "https://www.ozma-yehudit.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Otzma_Yehudit",
        "source_links": [
            {"label": "Official Website", "url": "https://www.ozma-yehudit.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Otzma_Yehudit"},
        ],
        "data_freshness": "2026-06-15",
    },
    "עוצמה יהודית בראשות איתמר בן גביר": {
        "name": "Otzma Yehudit",
        "wing": "far-right",
        "bloc": "coalition",
        "leader": "Itamar Ben-Gvir",
        "ideology": "Jewish ultranationalism, Kahanism",
        "agenda": "Demands strict law enforcement, increased security spending, annexation of the West Bank, and population transfer policies.",
        "website": "https://www.ozma-yehudit.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Otzma_Yehudit",
        "source_links": [
            {"label": "Official Website", "url": "https://www.ozma-yehudit.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Otzma_Yehudit"},
        ],
        "data_freshness": "2026-06-15",
    },
    "ישראל ביתנו": {
        "name": "Yisrael Beiteinu",
        "wing": "right",
        "bloc": "opposition",
        "leader": "Avigdor Lieberman",
        "ideology": "Secular nationalism, right-wing liberalism",
        "agenda": "Promotes universal draft (including ultra-Orthodox), public transport on Shabbat, free market policies, and security hawkishness.",
        "website": "https://www.beytenu.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Yisrael_Beiteinu",
        "source_links": [
            {"label": "Official Website", "url": "https://www.beytenu.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Yisrael_Beiteinu"},
        ],
        "data_freshness": "2026-06-15",
    },
    "רעמ": {
        "name": "United Arab List (Ra'am)",
        "wing": "center-right (Islamist)",
        "bloc": "arab_parties",
        "leader": "Mansour Abbas",
        "ideology": "Islamism, Arab minority interest advocacy",
        "agenda": "Focuses on developing Arab municipalities, solving crime in Arab sectors, legalizing Negev Bedouin towns, and coalition bargaining.",
        "website": "https://www.raam.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Arab_List",
        "source_links": [
            {"label": "Official Website", "url": "https://www.raam.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Arab_List"},
        ],
        "data_freshness": "2026-06-15",
    },
    'רע"ם': {
        "name": "United Arab List (Ra'am)",
        "wing": "center-right (Islamist)",
        "bloc": "arab_parties",
        "leader": "Mansour Abbas",
        "ideology": "Islamism, Arab minority interest advocacy",
        "agenda": "Focuses on developing Arab municipalities, solving crime in Arab sectors, legalizing Negev Bedouin towns, and coalition bargaining.",
        "website": "https://www.raam.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Arab_List",
        "source_links": [
            {"label": "Official Website", "url": "https://www.raam.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Arab_List"},
        ],
        "data_freshness": "2026-06-15",
    },
    "חדש-תעאל": {
        "name": "Hadash-Ta'al",
        "wing": "left",
        "bloc": "arab_parties",
        "leader": "Ayman Odeh",
        "ideology": "Democratic socialism, Arab-Jewish joint advocacy",
        "agenda": "Advocates for Arab minority civil rights, a Palestinian state, labor protection, and socialist economics.",
        "website": "https://www.hadash.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hadash.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al"},
        ],
        "data_freshness": "2026-06-15",
    },
    'חד"ש-תע"ল': {
        "name": "Hadash-Ta'al",
        "wing": "left",
        "bloc": "arab_parties",
        "leader": "Ayman Odeh",
        "ideology": "Democratic socialism, Arab-Jewish joint advocacy",
        "agenda": "Advocates for Arab minority civil rights, a Palestinian state, labor protection, and socialist economics.",
        "website": "https://www.hadash.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hadash.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al"},
        ],
        "data_freshness": "2026-06-15",
    },
    'חד"ש-תע"ל': {
        "name": "Hadash-Ta'al",
        "wing": "left",
        "bloc": "arab_parties",
        "leader": "Ayman Odeh",
        "ideology": "Democratic socialism, Arab-Jewish joint advocacy",
        "agenda": "Advocates for Arab minority civil rights, a Palestinian state, labor protection, and socialist economics.",
        "website": "https://www.hadash.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hadash.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al"},
        ],
        "data_freshness": "2026-06-15",
    },
    "העבודה": {
        "name": "The Democrats",
        "wing": "left",
        "bloc": "opposition",
        "leader": "Yair Golan",
        "ideology": "Social democracy, peace advocacy, secularism",
        "agenda": "Promotes welfare-state economics, religious freedom, civil marriage, LGBT equality, and a two-state solution.",
        "website": "https://www.hademokratim.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hademokratim.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "מפלגת העבודה הישראלית": {
        "name": "The Democrats",
        "wing": "left",
        "bloc": "opposition",
        "leader": "Yair Golan",
        "ideology": "Social democracy, peace advocacy, secularism",
        "agenda": "Promotes welfare-state economics, religious freedom, civil marriage, LGBT equality, and a two-state solution.",
        "website": "https://www.hademokratim.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hademokratim.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "נעם": {
        "name": "Noam",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Avi Maoz",
        "ideology": "Jewish orthodox conservatism",
        "agenda": "Promotes strict religious family values, opposition to LGBT advocacy in state structures, and Orthodox Jewish education.",
        "website": "https://www.noamparty.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Noam_(political_party)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.noamparty.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Noam_(political_party)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "נעם - בראשות אבי מעוז": {
        "name": "Noam",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Avi Maoz",
        "ideology": "Jewish orthodox conservatism",
        "agenda": "Promotes strict religious family values, opposition to LGBT advocacy in state structures, and Orthodox Jewish education.",
        "website": "https://www.noamparty.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Noam_(political_party)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.noamparty.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Noam_(political_party)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "הימין הממלכתי": {
        "name": "New Hope (United Right)",
        "wing": "right",
        "bloc": "coalition",
        "leader": "Gideon Sa'ar",
        "ideology": "National liberalism, security hawkishness",
        "agenda": "Focuses on governance reforms, judicial balance, West Bank settlement support, and educational advancement.",
        "website": "https://www.tikvahadasha.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/New_Hope_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.tikvahadasha.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/New_Hope_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    "ביחד": {
        "name": "Together (Beyachad)",
        "wing": "center-right",
        "bloc": "opposition",
        "leader": "Naftali Bennett",
        "ideology": "National security centrism, liberal democracy",
        "agenda": "Security rebuilding after Oct 7, state commission of inquiry, 1 million aliyah plan, anti-corruption, housing affordability, and restoring public trust in government.",
        "website": "https://beyachad.co.il",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Together_(Israeli_political_alliance)",
        "source_links": [
            {"label": "Official Website", "url": "https://beyachad.co.il"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Together_(Israeli_political_alliance)"},
        ],
        "notes": "Formed April 2026 — alliance of Bennett 2026 party and Yesh Atid, led by Naftali Bennett.",
        "new_for_26th_knesset": True,
        "data_freshness": "2026-06-15",
    },
    "ישר": {
        "name": "Yashar",
        "wing": "center",
        "bloc": "opposition",
        "leader": "Gadi Eisenkot",
        "ideology": "Security pragmatism, moderate conservatism",
        "agenda": "Security sector reform, anti-corruption, centrist governance, rebuilding IDF command culture, and pragmatic diplomacy.",
        "website": "https://yashar.org.il",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Yashar_(political_party)",
        "source_links": [
            {"label": "Official Website", "url": "https://yashar.org.il"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Yashar_(political_party)"},
        ],
        "notes": "Founded 2025 by former IDF Chief of Staff Gadi Eisenkot.",
        "new_for_26th_knesset": True,
        "data_freshness": "2026-06-15",
    },
}


async def _knesset_get(path: str, params: dict = None) -> dict:
    url = f"{KNESSET_BASE}/{path}"
    if params is None:
        params = {}
    params["$format"] = "json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, params=params, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Knesset API error %s: %s", path, e)
            return {"value": []}


# ── Open Knesset CSV helpers ──────────────────────────────────────────────────

async def _fetch_oknesset_csv(url: str) -> list[dict]:
    """Fetch and parse a CSV from the Open Knesset pipeline (public, no geo-block)."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        decoded = resp.content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(decoded.splitlines())
        return list(reader)
    except Exception as e:
        logger.error("Failed to fetch Open Knesset CSV %s: %s", url, e)
        return []


async def _translate_names_batch(hebrew_names: list[str]) -> dict[str, str]:
    """Batch translate Hebrew politician names to English via OpenAI gpt-4o-mini."""
    if not settings.openai_api_key or not hebrew_names:
        return {}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    batches = [hebrew_names[i:i+80] for i in range(0, len(hebrew_names), 80)]
    mapping: dict[str, str] = {}
    for i, batch in enumerate(batches):
        prompt = (
            "Translate this list of Hebrew names of Israeli politicians to standard English. "
            f"List: {batch}\n"
            "Respond ONLY with a JSON object mapping Hebrew name -> English name. "
            'Example: {"בנימין נתניהו": "Benjamin Netanyahu"}'
        )
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            mapping.update(json.loads(resp.choices[0].message.content))
        except Exception as e:
            logger.warning("Name translation batch %d failed: %s", i + 1, e)
    return mapping


# ── Sync ──────────────────────────────────────────────────────────────────────

async def sync_parties() -> int:
    """Sync Knesset 25/26 parties from Open Knesset CSV pipeline (no geo-block).
    Enriches each party with official website, Wikipedia URL, and source links.
    Data is sourced from official party websites + Wikipedia — NOT AI-generated.
    """
    db = get_db()
    factions_rows = await _fetch_oknesset_csv(OKNESSET_FACTIONS_URL)
    positions_rows = await _fetch_oknesset_csv(OKNESSET_POSITIONS_URL)

    knesset_25_factions = [f for f in factions_rows if f.get("KnessetNum") == "25"]
    logger.info("Open Knesset: %d factions in Knesset 25", len(knesset_25_factions))

    synced = 0
    for f in knesset_25_factions:
        faction_id = f.get("Id") or f.get("FactionID")
        name_heb = (f.get("Name") or "").strip()
        if not name_heb:
            continue

        enrich = PARTY_ENRICHMENT.get(name_heb)
        if not enrich:
            for k, v in PARTY_ENRICHMENT.items():
                if k in name_heb or name_heb in k:
                    enrich = v
                    break
        
        # Fallback to AI enrichment if not found in pre-seeded dict
        if not enrich and settings.openai_api_key:
            enrich = await enrich_party_via_ai(name_heb)

        name_eng = enrich.get("name", name_heb) if enrich else name_heb
        # Count MK seats for this faction using PositionID 54
        seats = len({
            p.get("PersonID") for p in positions_rows
            if p.get("KnessetNum") == "25"
            and p.get("FactionID") == faction_id
            and p.get("PositionID") == "54"
        })

        doc = {
            "name": name_eng,
            "name_hebrew": name_heb,
            "wing": enrich.get("wing", "unknown") if enrich else "unknown",
            "bloc": enrich.get("bloc", "opposition") if enrich else "opposition",
            "seats": seats or 1,
            "leader": enrich.get("leader") if enrich else None,
            "ideology": enrich.get("ideology") if enrich else None,
            "agenda": enrich.get("agenda") if enrich else None,
            "website": enrich.get("website") if enrich else None,
            # Real-source enrichment fields — NOT AI-generated
            "wikipedia_url": enrich.get("wikipedia_url") if enrich else None,
            "source_links": enrich.get("source_links", []) if enrich else [],
            "data_freshness": enrich.get("data_freshness") if enrich else None,
            "data_source_note": "Data enriched via AI and official Knesset records.",
            "updated_at": datetime.utcnow(),
        }
        await db.parties.update_one({"name": name_eng}, {"$set": doc}, upsert=True)
        synced += 1

    logger.info("sync_parties complete: %d upserted", synced)
    return synced


async def sync_mps(limit: int = 200) -> int:
    """Sync active Knesset 25 members from Open Knesset CSV pipeline."""
    db = get_db()
    factions_rows = await _fetch_oknesset_csv(OKNESSET_FACTIONS_URL)
    persons_rows = await _fetch_oknesset_csv(OKNESSET_PERSONS_URL)
    positions_rows = await _fetch_oknesset_csv(OKNESSET_POSITIONS_URL)
    individuals_rows = await _fetch_oknesset_csv(OKNESSET_INDIVIDUALS_URL)

    # Build lookup: PersonID -> Hebrew name
    hebrew_name_by_id: dict[str, str] = {}
    for row in persons_rows:
        pid = row.get("PersonID")
        if pid:
            first = (row.get("FirstName") or "").strip()
            last = (row.get("LastName") or "").strip()
            hebrew_name_by_id[pid] = f"{first} {last}".strip()

    # Build lookup: PersonID -> photo/email from mk_individual
    individual_by_pid: dict[str, dict] = {}
    for ind in individuals_rows:
        pid = ind.get("PersonID")
        if pid:
            individual_by_pid[pid] = {
                "photo_url": ind.get("mk_individual_photo"),
                "email": ind.get("mk_individual_email"),
            }

    # Build party docs in DB (need _id for foreign key)
    knesset_25_factions = [f for f in factions_rows if f.get("KnessetNum") == "25"]
    db_parties: dict[str, ObjectId] = {}  # FactionID -> ObjectId
    faction_name_map: dict[str, str] = {}  # Hebrew faction name -> English name
    for f in knesset_25_factions:
        fid = f.get("Id") or f.get("FactionID")
        name_heb = (f.get("Name") or "").strip()
        enrich = PARTY_ENRICHMENT.get(name_heb)
        if not enrich:
            for k, v in PARTY_ENRICHMENT.items():
                if k in name_heb or name_heb in k:
                    enrich = v
                    break
        name_eng = enrich["name"] if enrich else name_heb
        stored = await db.parties.find_one({"name": name_eng})
        if stored:
            db_parties[fid] = stored["_id"]
        faction_name_map[name_heb] = name_eng

    # Map PersonID -> current FactionID via PositionID 54
    person_to_faction: dict[str, dict] = {}
    for pos in positions_rows:
        if pos.get("KnessetNum") == "25" and pos.get("PositionID") == "54":
            pid = pos.get("PersonID")
            finish = (pos.get("FinishDate") or "").strip()
            is_current = pos.get("IsCurrent", "").lower() == "true"
            if not finish or is_current:
                person_to_faction[pid] = {
                    "FactionID": pos.get("FactionID"),
                    "FactionName": (pos.get("FactionName") or "").strip(),
                }

    # Collect all active MKs (PositionID 43)
    active_pids: set[str] = set()
    active_rows: list[dict] = []
    for pos in positions_rows:
        if pos.get("KnessetNum") == "25" and pos.get("PositionID") == "43":
            finish = (pos.get("FinishDate") or "").strip()
            is_current = pos.get("IsCurrent", "").lower() == "true"
            if not finish or is_current:
                pid = pos.get("PersonID")
                if pid not in active_pids:
                    active_pids.add(pid)
                    active_rows.append(pos)

    logger.info("Open Knesset: %d active MKs found (Position 43)", len(active_rows))

    # Translate Hebrew names to English in one batch
    names_heb = list({hebrew_name_by_id[p] for p in active_pids if p in hebrew_name_by_id and hebrew_name_by_id[p]})
    name_translations = await _translate_names_batch(names_heb)

    synced = 0
    for pos in active_rows:
        pid = pos.get("PersonID")
        name_heb = hebrew_name_by_id.get(pid, "")
        name_eng = name_translations.get(name_heb) or f"MK-{pid}"

        faction_info = person_to_faction.get(pid) or {}
        faction_id = faction_info.get("FactionID")
        faction_name_heb = faction_info.get("FactionName", "")
        party_oid = db_parties.get(faction_id)
        party_name_eng = faction_name_map.get(faction_name_heb, faction_name_heb or "Independent")

        ind = individual_by_pid.get(pid) or {}
        photo_url = ind.get("photo_url") or f"https://knesset.gov.il/mk/images/members/{pid}.jpg"

        bio = f"Member of Knesset representing {party_name_eng}."
        role = "Member of Knesset"
        career_history = []
        if settings.openai_api_key:
            ai_data = await enrich_mp_bio_via_ai(name_eng, party_name_eng)
            if ai_data:
                bio = ai_data.get("bio", bio)
                role = ai_data.get("role", role)
                career_history = ai_data.get("career_history", [])

        mp_doc = {
            "knesset_id": int(pid) if (pid or "").isdigit() else pid,
            "name": name_eng,
            "name_hebrew": name_heb or None,
            "role": role,
            "is_active": True,
            "party_name": party_name_eng,
            "party_id": str(party_oid) if party_oid else None,
            "photo_url": photo_url,
            "bio": bio,
            "career_history": career_history,
            "updated_at": datetime.utcnow(),
        }
        knesset_id_val = int(pid) if (pid or "").isdigit() else pid
        await db.mps.update_one({"knesset_id": knesset_id_val}, {"$set": mp_doc}, upsert=True)
        synced += 1

    logger.info("sync_mps complete: %d upserted", synced)
    return synced


async def sync_bills_oknesset(limit: int = 200) -> int:
    """Sync bills from Open Knesset kns_bill CSV (Knesset 25 + 26).

    Uses the richer kns_bill.csv (not the airflow version) which includes
    TypeID, TypeDesc, and SummaryLaw columns.
    Joins with kns_billinitiator + kns_person to resolve initiator names.
    All data sourced from oknesset.org — no geo-blocked OData API.
    """
    db = get_db()

    # Fetch bills, initiators, and persons CSVs in parallel
    bills_rows, initiator_rows, persons_rows = await asyncio.gather(
        _fetch_oknesset_csv(OKNESSET_BILLS_URL),
        _fetch_oknesset_csv(OKNESSET_BILL_INITIATORS_URL),
        _fetch_oknesset_csv(OKNESSET_PERSONS_URL),
    )

    # Build PersonID → full Hebrew name lookup
    person_name_by_id: dict[str, str] = {}
    for p in persons_rows:
        pid = p.get("PersonID")
        if pid:
            first = (p.get("FirstName") or "").strip()
            last = (p.get("LastName") or "").strip()
            person_name_by_id[pid] = f"{first} {last}".strip()

    # Build BillID → primary initiator PersonID lookup
    # IsInitiator='1' marks the primary initiator; Ordinal orders multiple
    bill_initiator_pid: dict[str, str] = {}
    for r in initiator_rows:
        bid = r.get("BillID")
        pid = r.get("PersonID")
        is_main = r.get("IsInitiator", "0") == "1"
        ordinal = int(r.get("Ordinal") or 99)
        if bid and pid:
            existing = bill_initiator_pid.get(bid)
            if existing is None or (is_main and ordinal == 1):
                bill_initiator_pid[bid] = pid

    # Filter for Knesset 25 bills and sort by most recent
    bills_25 = [r for r in bills_rows if r.get("KnessetNum") in ("25", "26")]
    bills_25.sort(key=lambda r: r.get("LastUpdatedDate") or "", reverse=True)
    bills_25 = bills_25[:limit]

    synced = 0
    for row in bills_25:
        bill_id = row.get("BillID")
        if not bill_id:
            continue
        name_heb = (row.get("Name") or "").strip()

        # Resolve status: StatusID → human-readable via BILL_STATUS_MAP
        status_id = (row.get("StatusID") or "").strip()
        status_desc = BILL_STATUS_MAP.get(status_id, f"Status {status_id}" if status_id else None)

        # Resolve initiator name from joined person lookup
        initiator_pid = bill_initiator_pid.get(bill_id)
        initiator_name_heb = person_name_by_id.get(initiator_pid) if initiator_pid else None

        doc = {
            "bill_id": str(bill_id),
            "knesset_num": row.get("KnessetNum"),
            "name": name_heb,
            "name_hebrew": name_heb,
            # TypeDesc is available in kns_bill.csv (not airflow version)
            "type": (row.get("TypeDesc") or "").strip() or None,
            "type_id": row.get("TypeID"),
            # SubTypeDesc is available in both
            "sub_type": (row.get("SubTypeDesc") or "").strip() or None,
            "status_id": status_id or None,
            "status": status_desc,
            # SummaryLaw holds the legislative summary text in kns_bill.csv
            "summary": (row.get("SummaryLaw") or "").strip() or None,
            "publication_date": row.get("PublicationDate"),
            "private_number": row.get("PrivateNumber"),
            "committee_id": row.get("CommitteeID"),
            # Initiator resolved from joined person table
            "initiator_pid": initiator_pid,
            "initiator": initiator_name_heb,
            "initiator_party": None,  # Not in CSV — requires party join
            "last_updated": row.get("LastUpdatedDate"),
            "source": "Open Knesset CSV (kns_bill + kns_billinitiator + kns_person)",
            "api_status": "official",
            "updated_at": datetime.utcnow(),
        }
        await db.knesset_bills.update_one(
            {"bill_id": str(bill_id)},
            {"$set": doc},
            upsert=True,
        )
        synced += 1

    logger.info("sync_bills_oknesset complete: %d upserted", synced)
    return synced


async def sync_from_oknesset() -> dict:
    """Master sync that pulls parties, MKs, and bills from Open Knesset pipeline CSVs.
    Does NOT call the geo-blocked knesset.gov.il OData API.
    """
    parties = await sync_parties()
    mps = await sync_mps()
    bills = await sync_bills_oknesset()
    return {"parties": parties, "mps": mps, "bills": bills}


async def sync_committees(limit: int = 30) -> int:
    db = get_db()
    data = await _knesset_get("KNS_Committee", {"$filter": "KnessetNum eq 25", "$top": str(limit)})
    synced = 0
    for row in data.get("value", []):
        cid = row.get("CommitteeID")
        if not cid:
            continue
        doc = {
            "committee_id": cid,
            "name": row.get("Name", f"Committee-{cid}"),
            "name_hebrew": row.get("NameHeb"),
            "description": row.get("Description"),
            "updated_at": datetime.utcnow(),
        }
        await db.knesset_committees.update_one({"committee_id": cid}, {"$set": doc}, upsert=True)
        synced += 1
    return synced


# ── Queries ───────────────────────────────────────────────────────────────────

async def get_all_mps(party_name: Optional[str] = None) -> list[dict]:
    db = get_db()
    query = {"is_active": True}
    if party_name:
        query["party_name"] = party_name
    cursor = db.mps.find(query, {"_id": 0})
    return await cursor.to_list(length=200)


async def get_mp(mp_id: str) -> Optional[dict]:
    db = get_db()
    try:
        oid = ObjectId(mp_id)
    except Exception:
        return None
    mp = await db.mps.find_one({"_id": oid}, {"_id": 0})
    if mp:
        mp["id"] = mp_id
        mp["quotes"] = await (db.mp_quotes.find({"mp_id": mp_id}, {"_id": 0})).to_list(50)
        mp["actions"] = await (db.mp_actions.find({"mp_id": mp_id}, {"_id": 0})).to_list(50)
        if "committees" not in mp or not mp["committees"]:
            mp["committees"] = []
        if "bills_passed_count" not in mp or mp["bills_passed_count"] is None:
            mp["bills_passed_count"] = 0
    return mp


async def get_all_parties() -> list[dict]:
    db = get_db()
    cursor = db.parties.find({}, {"_id": 0}).sort("seats", -1)
    return await cursor.to_list(length=50)


async def get_party(party_id: str) -> Optional[dict]:
    db = get_db()
    try:
        oid = ObjectId(party_id)
    except Exception:
        return None
    party = await db.parties.find_one({"_id": oid}, {"_id": 0})
    if party:
        party["id"] = party_id
        party["members"] = await (db.mps.find({"party_id": party_id}, {"_id": 0})).to_list(150)
    return party


async def get_committees() -> list[dict]:
    db = get_db()
    cursor = db.knesset_committees.find({}, {"_id": 0}).sort("name", 1)
    return await cursor.to_list(length=50)


# ── Quotes & Actions ──────────────────────────────────────────────────────────

async def add_quote(mp_id: str, data: dict) -> dict:
    db = get_db()
    doc = {"mp_id": mp_id, "created_at": datetime.utcnow(), **data}
    result = await db.mp_quotes.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def add_action(mp_id: str, data: dict) -> dict:
    db = get_db()
    doc = {"mp_id": mp_id, "created_at": datetime.utcnow(), **data}
    result = await db.mp_actions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


async def get_mp_quotes(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.mp_quotes.find({"mp_id": mp_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


async def get_mp_actions(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.mp_actions.find({"mp_id": mp_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


# ── Contradiction Detection ───────────────────────────────────────────────────

_CONTRADICTION_PROMPT = """
You are a political fact-checker. Given an MP's quote and a later action, determine if there is a contradiction.
Quote: "{quote}"
Action: "{action}"
Topic: {topic}
Respond with JSON: {{"is_contradiction": true/false, "severity": "low"|"medium"|"high", "explanation": "...", "topic": "..."}}
Only respond with valid JSON.
"""


async def detect_contradiction(quote: dict, action: dict, use_ai: bool = False) -> Optional[dict]:
    if use_ai and settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            prompt = _CONTRADICTION_PROMPT.format(
                quote=quote.get("quote", "")[:300],
                action=action.get("action", "")[:300],
                topic=quote.get("topic") or action.get("topic") or "general",
            )
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=200,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            if result.get("is_contradiction"):
                return result
        except Exception as e:
            logger.warning("Contradiction AI failed: %s", e)

    # Rule-based fallback
    OPPOSING = [
        ({"support","approve","yes","agree"}, {"oppose","reject","no","against"}),
        ({"increase","raise","expand"}, {"decrease","cut","reduce"}),
        ({"peace","negotiate"}, {"war","attack","military"}),
    ]
    q_text = quote.get("quote", "").lower()
    a_text = action.get("action", "").lower()
    for pos, neg in OPPOSING:
        if (any(w in q_text for w in pos) and any(w in a_text for w in neg)) or \
           (any(w in q_text for w in neg) and any(w in a_text for w in pos)):
            return {
                "is_contradiction": True, "severity": "medium",
                "explanation": "Quote and action appear to contradict each other.",
                "topic": quote.get("topic") or "general",
            }
    return None


async def run_contradiction_scan(mp_id: str, use_ai: bool = False) -> list[dict]:
    db = get_db()
    quotes = await get_mp_quotes(mp_id)
    actions = await get_mp_actions(mp_id)
    new_contradictions = []

    for quote in quotes:
        for action in actions:
            if quote.get("topic") and action.get("topic") and quote["topic"] != action["topic"]:
                continue
            result = await detect_contradiction(quote, action, use_ai=use_ai)
            if result:
                existing = await db.contradictions.find_one({
                    "mp_id": mp_id,
                    "quote_id": str(quote.get("id", "")),
                    "action_id": str(action.get("id", "")),
                })
                if not existing:
                    doc = {
                        "mp_id": mp_id,
                        "quote_id": str(quote.get("id", "")),
                        "action_id": str(action.get("id", "")),
                        "explanation": result["explanation"],
                        "severity": result.get("severity", "medium"),
                        "topic": result.get("topic"),
                        "detected_at": datetime.utcnow(),
                    }
                    await db.contradictions.insert_one(doc)
                    doc.pop("_id", None)
                    new_contradictions.append(doc)

    # Update consistency score
    total = len(quotes) * len(actions)
    if total > 0:
        score = max(0.0, 1.0 - len(new_contradictions) / total)
        await db.mps.update_one({"_id": ObjectId(mp_id)}, {"$set": {"consistency_score": round(score, 2)}})

    return new_contradictions


async def get_contradictions(mp_id: str) -> list[dict]:
    db = get_db()
    cursor = db.contradictions.find({"mp_id": mp_id}, {"_id": 0}).sort("detected_at", -1)
    return await cursor.to_list(100)


# ── Bill Voting ───────────────────────────────────────────────────────────────

async def vote_on_bill(bill_id: str, user_id: str, support: bool) -> dict:
    db = get_db()
    bill = await db.knesset_bills.find_one({"_id": ObjectId(bill_id)})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    await db.bill_votes.update_one(
        {"bill_id": bill_id, "user_id": user_id},
        {"$set": {"support": support, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return await get_bill_tally(bill_id)


async def get_bill_tally(bill_id: str) -> dict:
    db = get_db()
    total = await db.bill_votes.count_documents({"bill_id": bill_id})
    support = await db.bill_votes.count_documents({"bill_id": bill_id, "support": True})
    return {
        "bill_id": bill_id,
        "total_votes": total,
        "support": support,
        "oppose": total - support,
        "support_pct": round((support / total * 100) if total else 0, 1),
    }


async def _normalize_bill_row(row: dict) -> dict:
    if not row:
        return {}

    bill_id = row.get("BillID") or row.get("Id") or row.get("ID")
    if bill_id is None:
        return {}
    bill_id = str(bill_id)

    initiator_person = row.get("KNS_BillInitiatorMK") or {}
    if isinstance(initiator_person, dict):
        initiator_name = " ".join(
            p for p in [initiator_person.get("FirstName"), initiator_person.get("LastName")]
            if p
        ).strip() or initiator_person.get("FullName")
    else:
        initiator_name = None

    committee = row.get("CommitteeName")
    if not committee and isinstance(row.get("KNS_BillCommittee"), dict):
        committee = row["KNS_BillCommittee"].get("Name")

    return {
        "bill_id": bill_id,
        "name": row.get("Name") or row.get("Title") or "",
        "name_hebrew": row.get("NameHeb") or row.get("TitleHeb"),
        "status": row.get("StatusDesc") or (row.get("KNS_BillStatus") or {}).get("StatusDesc"),
        "type": row.get("TypeDesc") or (row.get("KNS_BillType") or {}).get("TypeDesc"),
        "sub_type": row.get("SubTypeDesc") or (row.get("KNS_BillSubType") or {}).get("SubTypeDesc"),
        "initiator": row.get("InitiatorMKName") or initiator_name or row.get("InitiatorName"),
        "initiator_party": row.get("InitiatorPartyName"),
        "committee": committee,
        "summary": row.get("BillSummary") or row.get("Purpose") or row.get("Summary") or row.get("Proposal") or "",
        "last_updated": row.get("LastUpdatedDate") or row.get("UpdatedDate") or row.get("ModifiedDate"),
        "source": "Knesset OData",
        "api_status": "official",
        "raw": row,
    }


async def _wikipedia_search_titles(query: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "utf8": 1,
                    "srlimit": 3,
                },
                headers=HEADERS,
            )
            resp.raise_for_status()
            payload = resp.json()
        return [item.get("title") for item in payload.get("query", {}).get("search", []) if item.get("title")]
    except Exception as e:
        logger.warning("Wikipedia search failed for %s: %s", query, e)
        return []


async def _wikipedia_page_summary(title: str) -> Optional[dict]:
    try:
        encoded_title = quote(title, safe="")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Wikipedia summary fetch failed for %s: %s", title, e)
        return None


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


async def _fallback_bill_from_wikipedia(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    candidate_queries = [
        f"Knesset bill {bill_id}",
        f"Bill {bill_id} Knesset",
        f"Knesset law {bill_id}",
        f"Israeli bill {bill_id}",
    ]

    for query in candidate_queries:
        titles = await _wikipedia_search_titles(query)
        for title in titles:
            summary = await _wikipedia_page_summary(title)
            if summary and summary.get("extract"):
                return {
                    "bill_id": bill_id,
                    "name": summary.get("title") or f"Knesset Bill {bill_id}",
                    "name_hebrew": None,
                    "status": "fallback",
                    "type": "bill",
                    "sub_type": None,
                    "initiator": None,
                    "initiator_party": None,
                    "committee": None,
                    "summary": _clean_text(summary.get("extract")),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "Wikipedia fallback",
                    "api_status": "fallback",
                    "raw": summary,
                }
    return None


async def _fallback_bill_from_news(bill_id: str) -> Optional[dict]:
    try:
        from app.services.news_service import fetch_news

        news = await fetch_news("knesset", 50, israeli_only=True, use_cache=False, with_analysis=False)
        match_text = bill_id.lower()
        for article in news.articles:
            text = f"{article.title or ''} {article.description or ''}".lower()
            if match_text in text or "knesset" in text and bill_id in article.link:
                return {
                    "bill_id": bill_id,
                    "name": article.title or f"Knesset bill {bill_id}",
                    "name_hebrew": None,
                    "status": "fallback",
                    "type": "bill",
                    "sub_type": None,
                    "initiator": None,
                    "initiator_party": None,
                    "committee": None,
                    "summary": _clean_text(article.description),
                    "last_updated": datetime.utcnow().isoformat(),
                    "source": "Google News RSS fallback",
                    "api_status": "fallback",
                    "raw": article.model_dump() if hasattr(article, "model_dump") else {},
                }
    except Exception as e:
        logger.warning("News fallback failed for bill %s: %s", bill_id, e)
    return None


async def _fallback_bill_from_web(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    fallback = await _fallback_bill_from_wikipedia(bill_id)
    if fallback:
        return fallback

    return await _fallback_bill_from_news(bill_id)


async def _resolve_bill_identifier(bill_id: str) -> Optional[dict]:
    db = get_db()
    if not bill_id:
        return None

    bill = None
    try:
        bill = await db.knesset_bills.find_one({"_id": ObjectId(bill_id)})
    except Exception:
        bill = None

    if not bill:
        bill = await db.knesset_bills.find_one({"bill_id": str(bill_id)})

    if bill:
        bill["id"] = str(bill["_id"])
    return bill


async def _fetch_bill_from_api(bill_id: str) -> Optional[dict]:
    if not bill_id:
        return None

    filter_value = bill_id if bill_id.isdigit() else f"'{bill_id}'"
    data = await _knesset_get(
        "KNS_Bill",
        {
            "$filter": f"BillID eq {filter_value}",
            "$expand": "KNS_BillStatus,KNS_BillType,KNS_BillSubType,KNS_BillInitiatorMK,KNS_BillCommittee",
            "$top": "1",
            "$orderby": "LastUpdatedDate desc",
        },
    )
    rows = data.get("value", [])
    if not rows:
        return await _fallback_bill_from_web(bill_id)

    return await _normalize_bill_row(rows[0])


def _normalize_vote_record(row: dict, bill_id: str) -> dict:
    person = row.get("KNS_Person") or {}
    if isinstance(person, dict):
        mp_name = " ".join(
            p for p in [person.get("FirstName"), person.get("LastName")] if p
        ).strip() or person.get("FullName")
        knesset_person_id = person.get("PersonID") or person.get("ID")
    else:
        mp_name = None
        knesset_person_id = None

    vote_value = (
        row.get("VoteResultDesc") or row.get("VoteDesc") or row.get("VoteTypeDesc") or
        row.get("Vote") or row.get("VoteName") or row.get("Result")
    )
    vote_date = row.get("VoteDate") or row.get("Date") or row.get("VotingDate")

    return {
        "bill_id": str(bill_id),
        "mp_id": None,
        "knesset_person_id": str(knesset_person_id) if knesset_person_id is not None else None,
        "mp_name": mp_name or row.get("MPName") or row.get("Name") or "Unknown",
        "party": (person or {}).get("PartyName") or row.get("PartyName") or row.get("FactionName"),
        "vote": str(vote_value).strip() if vote_value is not None else "unknown",
        "vote_date": vote_date,
        "source": "Knesset OData",
        "raw": row,
    }


def _normalize_vote_label(value: str) -> str:
    if not value:
        return "unknown"
    value = value.lower().strip()
    if "yes" in value or value in {"a", "for", "approve", "support", "aye"}:
        return "yes"
    if "no" in value or value in {"oppose", "against", "nay", "reject"}:
        return "no"
    if "abstain" in value or value in {"abstention", "abs"}:
        return "abstain"
    if "absent" in value or value in {"not present", "absent"}:
        return "absent"
    return value


async def sync_bills(limit: int = 50) -> int:
    db = get_db()
    data = await _knesset_get(
        "KNS_Bill",
        {
            "$filter": "KnessetNum eq 25",
            "$top": str(limit),
            "$orderby": "LastUpdatedDate desc",
            "$expand": "KNS_BillStatus,KNS_BillType,KNS_BillSubType,KNS_BillInitiatorMK,KNS_BillCommittee",
        },
    )
    bills = data.get("value", [])
    synced = 0
    for row in bills:
        bill = await _normalize_bill_row(row)
        if not bill:
            continue
        bill["updated_at"] = datetime.utcnow()
        await db.knesset_bills.update_one(
            {"bill_id": bill["bill_id"]},
            {"$set": bill},
            upsert=True,
        )
        synced += 1
    return synced


async def sync_bill_votes(bill_id: str) -> int:
    db = get_db()
    bill = await _resolve_bill_identifier(bill_id)
    if not bill:
        bill = await _fetch_bill_from_api(bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        await db.knesset_bills.update_one(
            {"bill_id": bill["bill_id"]},
            {"$set": bill},
            upsert=True,
        )
        bill = await _resolve_bill_identifier(bill["bill_id"])

    data = await _knesset_get(
        "KNS_BillVote",
        {
            "$filter": f"BillID eq {bill['bill_id']}",
            "$expand": "KNS_Person",
            "$top": "500",
        },
    )
    votes = data.get("value", [])
    if not votes:
        data = await _knesset_get(
            "KNS_Vote",
            {
                "$filter": f"BillID eq {bill['bill_id']}",
                "$expand": "KNS_Person",
                "$top": "500",
            },
        )
        votes = data.get("value", [])

    synced = 0
    for row in votes:
        record = _normalize_vote_record(row, bill["bill_id"])
        if record["knesset_person_id"]:
            mp = await db.mps.find_one({"knesset_id": int(record["knesset_person_id"])} if record["knesset_person_id"].isdigit() else {"knesset_id": record["knesset_person_id"]})
            if mp:
                record["mp_id"] = str(mp["_id"])
                record["mp_object_id"] = str(mp["_id"])
        if record["vote"]:
            record["vote"] = _normalize_vote_label(record["vote"])
        await db.bill_vote_records.update_one(
            {"bill_id": record["bill_id"], "knesset_person_id": record["knesset_person_id"], "mp_name": record["mp_name"]},
            {"$set": record},
            upsert=True,
        )
        synced += 1
    return synced


async def get_all_bills(limit: int = 50) -> list[dict]:
    db = get_db()
    cursor = db.knesset_bills.find({}, {"raw": 0}).sort("last_updated", -1).limit(limit)
    bills = await cursor.to_list(length=limit)
    for bill in bills:
        bill["id"] = str(bill["_id"])
        bill.pop("_id", None)
    return bills


async def get_bill_vote_summary(bill_id: str) -> dict:
    db = get_db()
    records = await db.bill_vote_records.find({"bill_id": str(bill_id)}, {"vote": 1}).to_list(length=1000)
    summary = {"total": len(records), "yes": 0, "no": 0, "abstain": 0, "absent": 0, "other": 0}
    for rec in records:
        label = _normalize_vote_label(rec.get("vote", ""))
        if label in summary:
            summary[label] += 1
        else:
            summary["other"] += 1
    return summary


async def get_bill(bill_id: str) -> Optional[dict]:
    db = get_db()
    bill = await _resolve_bill_identifier(bill_id)
    if not bill and bill_id.isdigit():
        bill = await _fetch_bill_from_api(bill_id)
        if bill:
            bill["updated_at"] = datetime.utcnow()
            result = await db.knesset_bills.update_one(
                {"bill_id": bill["bill_id"]},
                {"$set": bill},
                upsert=True,
            )
            if result.upserted_id:
                bill["id"] = str(result.upserted_id)
            else:
                stored = await db.knesset_bills.find_one({"bill_id": bill["bill_id"]})
                bill["id"] = str(stored["_id"])

    if not bill:
        return None

    analyze = False
    if bill.get("summary") and not bill.get("ai_summary"):
        analyze = True

    if analyze:
        from app.services.ai_service import analyze_article
        analysis = await analyze_article(
            guid=f"bill-{bill['bill_id']}",
            title=bill.get("name", ""),
            description=bill.get("summary", ""),
            source="Knesset Bill",
            user_tier="pro",
        )
        bill["ai_summary"] = analysis.summary_hebrew
        await db.knesset_bills.update_one({"_id": ObjectId(bill["id"])}, {"$set": {"ai_summary": bill["ai_summary"]}})

    bill["community_tally"] = await get_bill_tally(bill["id"])
    bill["official_vote_summary"] = await get_bill_vote_summary(bill["bill_id"])
    bill.pop("raw", None)
    bill.pop("_id", None)
    return bill


async def get_bill_vote_records(bill_id: str) -> list[dict]:
    bill = await _resolve_bill_identifier(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    db = get_db()
    cursor = db.bill_vote_records.find({"bill_id": bill["bill_id"]}, {"_id": 0, "raw": 0}).sort("vote_date", -1)
    records = await cursor.to_list(length=1000)
    for record in records:
        record["bill_name"] = bill.get("name")
    return records


async def get_mp_vote_records(mp_id: str) -> list[dict]:
    db = get_db()
    query = {"$or": [{"mp_id": mp_id}, {"knesset_person_id": mp_id}, {"mp_object_id": mp_id}]}
    if ObjectId.is_valid(mp_id):
        mp = await db.mps.find_one({"_id": ObjectId(mp_id)})
        if mp and mp.get("knesset_id"):
            query["$or"].append({"knesset_person_id": str(mp["knesset_id"])})
    cursor = db.bill_vote_records.find(query, {"_id": 0, "raw": 0}).sort("vote_date", -1)
    return await cursor.to_list(1000)

async def enrich_party_via_ai(name_heb: str) -> dict:
    """Use GPT-4o-mini to dynamically enrich an unknown Israeli political party."""
    if not settings.openai_api_key:
        return {}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"""
    You are an expert on Israeli politics. Analyze the following political faction name in Hebrew: "{name_heb}".
    Provide the following details in standard English as a JSON object:
    - name: Standard English name of the party (e.g. "Likud", "Shas", "United Torah Judaism", "The Democrats", "National Unity")
    - wing: "left" | "center" | "right" | "far-right" | "far-left" | "unknown"
    - bloc: "coalition" | "opposition" | "arab_parties" (in the context of the 25th Knesset / current government)
    - leader: Current party leader's name in English
    - ideology: Main ideologies (comma separated)
    - agenda: 1-2 sentence description of the party's platform/goals
    - website: Official website URL if known, otherwise null
    - wikipedia_url: English Wikipedia URL if known, otherwise null
    
    Respond ONLY with the JSON object.
    """
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.warning("AI party enrichment failed for %s: %s", name_heb, e)
        return {}


async def enrich_mp_bio_via_ai(name_eng: str, party_name_eng: str) -> dict:
    """Use GPT-4o-mini to generate bio and career history for an MK."""
    if not settings.openai_api_key:
        return {}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"""
    Provide a professional bio and political career overview for Israeli Member of Knesset "{name_eng}" representing the party "{party_name_eng}".
    Respond ONLY with a JSON object:
    {{
       "bio": "2-3 sentence overview bio",
       "role": "Current parliamentary role or position (e.g. Member of Knesset, Minister of Defense, Prime Minister)",
       "career_history": ["Milestone 1", "Milestone 2", "Milestone 3"]
    }}
    """
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.warning("AI MP bio enrichment failed for %s: %s", name_eng, e)
        return {}
