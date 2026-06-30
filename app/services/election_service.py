# app/services/election_service.py
"""
2026 Israeli Legislative Election (26th Knesset) data service.

ALL DATA IS SOURCE-VERIFIED — not AI-generated.
Sources: Wikipedia, bechirot.gov.il (Central Elections Committee),
         Times of Israel, Israel Policy Forum, official party websites.
Last verified: 2026-06-15
"""

from datetime import datetime

# ── 2026 Election Overview ────────────────────────────────────────────────────
ELECTION_2026_OVERVIEW = {
    "knesset_number": 26,
    "scheduled_date": "2026-10-27",
    "possible_early_date": "September 2026",
    "date_confirmed": False,
    "date_note": "Knesset began dissolution proceedings as of June 2026; final date not yet set.",
    "total_seats": 120,
    "electoral_threshold_pct": 3.25,
    "electoral_threshold_seats": 4,  # approximate minimum to pass threshold
    "official_authority": "Central Elections Committee (ועדת הבחירות המרכזית)",
    "official_source": "https://www.bechirot.gov.il/",
    "knesset_source": "https://www.knesset.gov.il/",
    "wikipedia_source": "https://en.wikipedia.org/wiki/2026_Israeli_legislative_election",
    "context": (
        "The 26th Knesset election is viewed as a referendum on PM Netanyahu's leadership "
        "and his handling of the October 7, 2023 Hamas attack and subsequent war. "
        "The election comes amid major political realignments, including the formation of "
        "the 'Together' (Beyachad) alliance by Naftali Bennett and Yair Lapid, and the "
        "emergence of Gadi Eisenkot's Yashar party."
    ),
    "data_source_note": "Election date and context sourced from Wikipedia and Israel Policy Forum — not AI-generated.",
    "data_freshness": "2026-06-15",
}

# ── Key Campaign Issues ────────────────────────────────────────────────────────
ELECTION_2026_ISSUES = [
    {
        "issue": "October 7 Accountability",
        "description": (
            "Establishment of a state commission of inquiry into the October 7, 2023 Hamas attack "
            "and the government's failures. A central demand of the opposition and bereaved families."
        ),
        "camps": {
            "for": ["Together (Beyachad)", "Yashar", "The Democrats", "Yisrael Beiteinu"],
            "against": ["Likud", "Shas", "United Torah Judaism", "Religious Zionism"],
        },
        "wikipedia": "https://en.wikipedia.org/wiki/2023_Hamas-led_attack_on_Israel",
    },
    {
        "issue": "Ultra-Orthodox Military Conscription",
        "description": (
            "Whether Haredi yeshiva students should serve in the IDF. The Supreme Court ruled in 2024 "
            "that existing exemptions are unconstitutional. Coalition parties Shas and UTJ strongly oppose conscription."
        ),
        "camps": {
            "for_conscription": ["Yisrael Beiteinu", "Yashar", "Together", "The Democrats"],
            "against_conscription": ["Shas", "United Torah Judaism"],
        },
        "wikipedia": "https://en.wikipedia.org/wiki/Haredi_Jewish_military_service_in_Israel",
    },
    {
        "issue": "Judicial Reform / Constitutionalism",
        "description": (
            "Ongoing debate over the 2023 judicial overhaul that weakened the Supreme Court. "
            "Most of the opposition wants to reverse or limit these changes."
        ),
        "wikipedia": "https://en.wikipedia.org/wiki/2023_Israeli_judicial_reform",
    },
    {
        "issue": "Netanyahu Trial & Term Limits",
        "description": (
            "PM Netanyahu is on trial for corruption. Opposition parties have proposed legislation "
            "to limit the terms of prime ministers. Netanyahu rejects any such limits."
        ),
        "wikipedia": "https://en.wikipedia.org/wiki/Legal_proceedings_against_Benjamin_Netanyahu",
    },
    {
        "issue": "Hostage Deal & Gaza War Endgame",
        "description": (
            "The fate of hostages still held in Gaza and the terms of any ceasefire or deal. "
            "This is a deeply emotional issue dividing Israeli society."
        ),
    },
    {
        "issue": "Housing and Cost of Living",
        "description": (
            "Israel faces a severe housing shortage and high cost of living. "
            "Together and Yashar have both made this a key economic platform pillar."
        ),
    },
    {
        "issue": "Israeli-Arab Sector: Crime and Development",
        "description": (
            "High crime rates in Arab communities have become a major political issue. "
            "Ra'am focuses on investment in Arab municipalities and crime reduction."
        ),
    },
]

# ── Parties for 2026 Election ─────────────────────────────────────────────────
# Data sourced from: Wikipedia, Times of Israel, official party websites, Israel Policy Forum
# Polling ranges are approximate as of June 2026 (vary by pollster)
ELECTION_2026_PARTIES = [
    # ── OPPOSITION BLOC ──────────────────────────────────────────────────────
    {
        "name": "Together (Beyachad)",
        "name_hebrew": "ביחד",
        "leader": "Naftali Bennett",
        "wing": "center-right",
        "bloc": "opposition",
        "new_for_2026": True,
        "formed_from": ["Bennett 2026", "Yesh Atid (Lapid)"],
        "formed_date": "April 2026",
        "ideology": "National security centrism, liberal democracy",
        "key_platform": [
            "State commission of inquiry into October 7",
            "Security rebuilding — military, intelligence reform",
            "Plan to bring 1 million new immigrants (olim) in 10 years",
            "Anti-corruption legislation",
            "Housing affordability reform",
            "Restoring public trust in government institutions",
        ],
        "poll_seats_range": "18–24",
        "poll_source": "Times of Israel / various pollsters, June 2026",
        "official_website": "https://beyachad.co.il",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Together_(Israeli_political_alliance)",
        "source_links": [
            {"label": "Official Website", "url": "https://beyachad.co.il"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Together_(Israeli_political_alliance)"},
            {"label": "Times of Israel", "url": "https://www.timesofisrael.com/topic/bennett/"},
        ],
        "notes": "Bennett leads; Lapid is number two on the list. First polling as a combined force showed it as the largest or second-largest party.",
        "data_freshness": "2026-06-15",
    },
    {
        "name": "Yashar",
        "name_hebrew": "ישר",
        "leader": "Gadi Eisenkot",
        "wing": "center",
        "bloc": "opposition",
        "new_for_2026": True,
        "formed_date": "2025",
        "ideology": "Security pragmatism, moderate centre",
        "key_platform": [
            "Rebuilding IDF command culture and security establishment",
            "Anti-corruption and clean governance",
            "Centrist, pragmatic policy between coalition and left-wing opposition",
            "Accountability for October 7",
        ],
        "poll_seats_range": "14–20",
        "poll_source": "Times of Israel / various pollsters, June 2026",
        "official_website": "https://yashar.org.il",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Yashar_(political_party)",
        "source_links": [
            {"label": "Official Website", "url": "https://yashar.org.il"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Yashar_(political_party)"},
        ],
        "notes": "Eisenkot served as IDF Chief of Staff 2015–2019, and as a minister under Lapid. His party attracts security-minded centrist voters.",
        "data_freshness": "2026-06-15",
    },
    {
        "name": "Yisrael Beiteinu",
        "name_hebrew": "ישראל ביתנו",
        "leader": "Avigdor Lieberman",
        "wing": "right",
        "bloc": "opposition",
        "ideology": "Secular nationalism, economic liberalism",
        "key_platform": [
            "Universal military draft (including ultra-Orthodox)",
            "Secular state — public transport on Shabbat",
            "Free-market economic reforms",
            "Strong stance against Hamas and Palestinian Authority",
        ],
        "poll_seats_range": "8–12",
        "official_website": "https://www.beytenu.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Yisrael_Beiteinu",
        "source_links": [
            {"label": "Official Website", "url": "https://www.beytenu.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Yisrael_Beiteinu"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "National Unity",
        "name_hebrew": "המחנה הממלכתי",
        "leader": "Benny Gantz",
        "wing": "center",
        "bloc": "opposition",
        "ideology": "Liberal Zionism, security centrism",
        "key_platform": [
            "State stability and consensus building",
            "Judicial balance and preservation",
            "Pragmatic security policy",
        ],
        "poll_seats_range": "6–10",
        "official_website": "https://www.machane.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.machane.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/National_Unity_(Israel)"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "The Democrats",
        "name_hebrew": "הדמוקרטים",
        "leader": "Yair Golan",
        "wing": "left",
        "bloc": "opposition",
        "ideology": "Social democracy, peace advocacy",
        "key_platform": [
            "Two-state solution",
            "Welfare economics and social equality",
            "Civil marriage and LGBT rights",
            "Religious pluralism",
        ],
        "poll_seats_range": "6–10",
        "official_website": "https://www.hademokratim.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hademokratim.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/The_Democrats_(Israel)"},
        ],
        "notes": "Merger of Labor and Meretz parties, led by former deputy IDF Chief Yair Golan.",
        "data_freshness": "2026-06-15",
    },
    # ── COALITION BLOC ───────────────────────────────────────────────────────
    {
        "name": "Likud",
        "name_hebrew": "הליכוד",
        "leader": "Benjamin Netanyahu",
        "wing": "right",
        "bloc": "coalition",
        "ideology": "National liberalism, conservatism",
        "key_platform": [
            "Completing the war goals in Gaza",
            "Normalization with Saudi Arabia",
            "Economic growth through deregulation",
            "Jewish identity and heritage",
        ],
        "poll_seats_range": "20–24",
        "official_website": "https://www.likud.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Likud",
        "source_links": [
            {"label": "Official Website", "url": "https://www.likud.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Likud"},
            {"label": "Knesset Page", "url": "https://www.knesset.gov.il/faction/eng/FactionPage_eng.asp?pgm=1"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "Shas",
        "name_hebrew": "ש\"ס",
        "leader": "Aryeh Deri",
        "wing": "right",
        "bloc": "coalition",
        "ideology": "Religious conservatism, Sephardic advocacy",
        "key_platform": [
            "Welfare support for lower-income Sephardic families",
            "Religious education funding",
            "Opposing ultra-Orthodox military conscription",
            "Traditional Jewish values in public life",
        ],
        "poll_seats_range": "9–12",
        "official_website": "https://www.shas.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Shas",
        "source_links": [
            {"label": "Official Website", "url": "https://www.shas.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Shas"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "United Torah Judaism",
        "name_hebrew": "יהדות התורה",
        "leader": "Yitzhak Goldknopf",
        "wing": "right",
        "bloc": "coalition",
        "ideology": "Ultra-Orthodox Judaism",
        "key_platform": [
            "Yeshiva student military service exemption",
            "Haredi education autonomy",
            "Housing subsidies for large families",
            "Preservation of religious status quo",
        ],
        "poll_seats_range": "8–10",
        "official_website": "https://www.degeltorah.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Torah_Judaism",
        "source_links": [
            {"label": "Official Website", "url": "https://www.degeltorah.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Torah_Judaism"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "Religious Zionism",
        "name_hebrew": "הציונות הדתית",
        "leader": "Bezalel Smotrich",
        "wing": "far-right",
        "bloc": "coalition",
        "ideology": "Religious nationalism, ultranationalism",
        "key_platform": [
            "Annexation of the West Bank",
            "Settlement expansion",
            "Complete victory in Gaza (no ceasefire)",
            "Conservative religious legislation",
        ],
        "poll_seats_range": "6–9",
        "official_website": "https://www.dati.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party",
        "source_links": [
            {"label": "Official Website", "url": "https://www.dati.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Religious_Zionism_Party"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "Otzma Yehudit",
        "name_hebrew": "עוצמה יהודית",
        "leader": "Itamar Ben-Gvir",
        "wing": "far-right",
        "bloc": "coalition",
        "ideology": "Jewish ultranationalism, Kahanism",
        "key_platform": [
            "Mass deportation of hostile populations",
            "Re-occupation of Gaza",
            "Strict policing and security crackdowns",
            "Jewish sovereignty over all biblical Israel",
        ],
        "poll_seats_range": "5–9",
        "official_website": "https://www.ozma-yehudit.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Otzma_Yehudit",
        "source_links": [
            {"label": "Official Website", "url": "https://www.ozma-yehudit.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Otzma_Yehudit"},
        ],
        "data_freshness": "2026-06-15",
    },
    # ── ARAB PARTIES ─────────────────────────────────────────────────────────
    {
        "name": "Hadash-Ta'al",
        "name_hebrew": "חד\"ש-תע\"ל",
        "leader": "Ayman Odeh",
        "wing": "left",
        "bloc": "arab_parties",
        "ideology": "Democratic socialism, Arab-Jewish co-existence",
        "key_platform": [
            "Two-state solution and Palestinian rights",
            "Arab minority civil equality in Israel",
            "Social democratic economics",
            "Immediate ceasefire in Gaza",
        ],
        "poll_seats_range": "5–8",
        "official_website": "https://www.hadash.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al",
        "source_links": [
            {"label": "Official Website", "url": "https://www.hadash.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Hadash%E2%80%93Ta%27al"},
        ],
        "data_freshness": "2026-06-15",
    },
    {
        "name": "United Arab List (Ra'am)",
        "name_hebrew": "רע\"ם",
        "leader": "Mansour Abbas",
        "wing": "center-right (Islamist)",
        "bloc": "arab_parties",
        "ideology": "Islamism, pragmatic Arab minority advocacy",
        "key_platform": [
            "Developing Arab municipalities and infrastructure",
            "Combating crime in the Arab sector",
            "Legalizing Negev Bedouin villages",
            "Pragmatic coalition bargaining for Arab community gains",
        ],
        "poll_seats_range": "4–6",
        "official_website": "https://www.raam.org.il/",
        "wikipedia_url": "https://en.wikipedia.org/wiki/United_Arab_List",
        "source_links": [
            {"label": "Official Website", "url": "https://www.raam.org.il/"},
            {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/United_Arab_List"},
        ],
        "data_freshness": "2026-06-15",
    },
]

# ── Bloc Projections ──────────────────────────────────────────────────────────
ELECTION_2026_BLOCS = {
    "coalition_right": {
        "label": "Current Coalition Bloc (Right)",
        "parties": ["Likud", "Shas", "United Torah Judaism", "Religious Zionism", "Otzma Yehudit"],
        "poll_seats_approx": 50,
        "majority_needed": 61,
        "note": "Consistently polling below the 61-seat majority needed to form a government (as of June 2026).",
        "source": "Times of Israel / various Israeli pollsters",
    },
    "zionist_opposition": {
        "label": "Zionist Opposition Bloc",
        "parties": ["Together (Beyachad)", "Yashar", "Yisrael Beiteinu", "National Unity", "The Democrats"],
        "poll_seats_approx": 58,
        "majority_needed": 61,
        "note": "Needs Arab party support to reach 61 seats for a majority government.",
        "source": "Times of Israel / various Israeli pollsters",
    },
    "arab_parties": {
        "label": "Arab Parties",
        "parties": ["Hadash-Ta'al", "United Arab List (Ra'am)"],
        "poll_seats_approx": 12,
        "note": "Their support of an opposition government would be required for a majority.",
    },
}

# ── Authoritative Sources ─────────────────────────────────────────────────────
# 22 sources covering: official government, Hebrew news, English news, Arabic news,
# think tanks, polling bodies, and international outlets with Israel focus.
ELECTION_2026_SOURCES = [
    # ── OFFICIAL GOVERNMENT ──────────────────────────────────────────────────
    {
        "name": "Central Elections Committee (ועדת הבחירות המרכזית)",
        "description": "The official Israeli government authority for all election information. Final candidate lists, election date, and official results will be published here.",
        "url": "https://www.bechirot.gov.il/",
        "type": "official_government",
        "language": "Hebrew / English",
        "reliability": "authoritative",
        "bias_note": "neutral — official body",
    },
    {
        "name": "Knesset Official Website",
        "description": "Official website of the Israeli parliament. Current party/faction pages, MK profiles, bill status, and legislative data.",
        "url": "https://www.knesset.gov.il/",
        "type": "official_government",
        "language": "Hebrew / English",
        "reliability": "authoritative",
        "bias_note": "neutral — official body",
    },
    {
        "name": "Government Press Office (GPO)",
        "description": "Official Israeli government press releases, statements, and announcements from ministries and the Prime Minister's office.",
        "url": "https://www.gov.il/en/",
        "type": "official_government",
        "language": "Hebrew / English",
        "reliability": "authoritative",
        "bias_note": "official government voice",
    },

    # ── HEBREW-LANGUAGE NEWS ─────────────────────────────────────────────────
    {
        "name": "Ynet News (ידיעות אחרונות)",
        "description": "Israel's highest-traffic news website. Owned by Yedioth Ahronoth group. Extensive election coverage, polls, and political analysis in Hebrew.",
        "url": "https://www.ynet.co.il/",
        "type": "news_outlet",
        "language": "Hebrew (English section: ynetnews.com)",
        "reliability": "high",
        "bias_note": "center",
        "english_url": "https://www.ynetnews.com/",
    },
    {
        "name": "Kan News (כאן חדשות)",
        "description": "Israel's public broadcaster (equivalent of BBC). Considered the most balanced and authoritative Hebrew-language TV news source.",
        "url": "https://www.kan.org.il/news/",
        "type": "public_broadcaster",
        "language": "Hebrew",
        "reliability": "very high",
        "bias_note": "center — public broadcaster",
    },
    {
        "name": "Walla! News (וואלה חדשות)",
        "description": "Major Israeli news portal. Strong political desk with breaking news and election polls.",
        "url": "https://news.walla.co.il/",
        "type": "news_outlet",
        "language": "Hebrew",
        "reliability": "high",
        "bias_note": "center",
    },
    {
        "name": "Maariv (מעריב)",
        "description": "One of Israel's oldest daily newspapers. Active political reporting and election analysis.",
        "url": "https://www.maariv.co.il/",
        "type": "news_outlet",
        "language": "Hebrew",
        "reliability": "high",
        "bias_note": "center-right",
    },
    {
        "name": "Haaretz (הארץ)",
        "description": "Israeli daily newspaper — left-leaning. Known for in-depth investigative political reporting and critical analysis of the government.",
        "url": "https://www.haaretz.com/",
        "type": "news_outlet",
        "language": "English / Hebrew",
        "reliability": "high (note: editorial slant)",
        "bias_note": "center-left",
    },
    {
        "name": "Israel Hayom (ישראל היום)",
        "description": "Israel's most widely-distributed Hebrew daily (free newspaper). Generally supportive of Likud/Netanyahu. Important for understanding coalition base coverage.",
        "url": "https://www.israelhayom.co.il/",
        "type": "news_outlet",
        "language": "Hebrew / English",
        "reliability": "medium-high (note: editorial slant)",
        "bias_note": "right / pro-Netanyahu",
        "english_url": "https://www.israelhayom.com/",
    },
    {
        "name": "Arutz Sheva / Israel National News",
        "description": "Right-wing / religious Zionist news outlet. Represents the settler and national-religious perspective in Israeli politics.",
        "url": "https://www.israelnationalnews.com/",
        "type": "news_outlet",
        "language": "English / Hebrew",
        "reliability": "medium (note: strong editorial slant)",
        "bias_note": "right / religious Zionist",
    },

    # ── ENGLISH-LANGUAGE NEWS ────────────────────────────────────────────────
    {
        "name": "Times of Israel",
        "description": "English-language Israeli news outlet with comprehensive election coverage including polling, party platforms, and analysis.",
        "url": "https://www.timesofisrael.com/",
        "type": "news_outlet",
        "language": "English",
        "reliability": "high",
        "bias_note": "center",
    },
    {
        "name": "Jerusalem Post",
        "description": "Israeli daily newspaper — center-right. Broad coverage of Israeli politics in English. Widely read internationally.",
        "url": "https://www.jpost.com/",
        "type": "news_outlet",
        "language": "English",
        "reliability": "high (note: editorial slant)",
        "bias_note": "center-right",
    },
    {
        "name": "i24 News",
        "description": "International news channel based in Israel. Covers Israeli politics from a global perspective in English, French, and Arabic.",
        "url": "https://www.i24news.tv/en",
        "type": "news_outlet",
        "language": "English / French / Arabic",
        "reliability": "high",
        "bias_note": "center",
    },
    {
        "name": "Reuters – Israel Coverage",
        "description": "International wire agency. Neutral, factual reporting on Israeli election developments. Widely cited as a primary source by other outlets.",
        "url": "https://www.reuters.com/world/middle-east/",
        "type": "wire_agency",
        "language": "English",
        "reliability": "very high",
        "bias_note": "neutral — wire agency",
    },
    {
        "name": "Associated Press (AP) – Israel",
        "description": "Global wire agency. Neutral factual coverage of Israeli politics and elections.",
        "url": "https://apnews.com/hub/israel",
        "type": "wire_agency",
        "language": "English",
        "reliability": "very high",
        "bias_note": "neutral — wire agency",
    },
    {
        "name": "BBC News – Middle East",
        "description": "British public broadcaster. Extensive, internationally balanced coverage of Israeli politics and elections.",
        "url": "https://www.bbc.com/news/world/middle_east",
        "type": "public_broadcaster",
        "language": "English",
        "reliability": "very high",
        "bias_note": "center — public broadcaster",
    },

    # ── ARABIC-LANGUAGE NEWS ─────────────────────────────────────────────────
    {
        "name": "Al Jazeera – Israel/Palestine",
        "description": "Qatar-based pan-Arab broadcaster. Provides Arab-world perspective on Israeli elections and Palestinian affairs. Widely read in Arabic-speaking communities inside Israel.",
        "url": "https://www.aljazeera.com/where/israel/",
        "type": "news_outlet",
        "language": "Arabic / English",
        "reliability": "high (note: editorial perspective)",
        "bias_note": "pro-Palestinian perspective",
    },
    {
        "name": "BBC Arabic",
        "description": "Arabic-language service of the BBC. Neutral and balanced coverage of Israeli and Middle East politics for Arabic-speaking audiences.",
        "url": "https://www.bbc.com/arabic",
        "type": "public_broadcaster",
        "language": "Arabic",
        "reliability": "very high",
        "bias_note": "center — public broadcaster",
    },

    # ── THINK TANKS & RESEARCH ───────────────────────────────────────────────
    {
        "name": "Israel Democracy Institute (IDI)",
        "description": "Non-partisan research institute. Publishes the Israeli Democracy Index, electoral polls, and policy analysis. Primary data source for election research.",
        "url": "https://www.idi.org.il/en/",
        "type": "think_tank",
        "language": "English / Hebrew",
        "reliability": "very high",
        "bias_note": "non-partisan — academic",
    },
    {
        "name": "Israel Policy Forum",
        "description": "Policy research organization with in-depth analysis of Israeli politics, elections, and peace process issues.",
        "url": "https://israelpolicyforum.org/",
        "type": "think_tank",
        "language": "English",
        "reliability": "high",
        "bias_note": "center-left — pro-two-state",
    },
    {
        "name": "Mitvim – The Israeli Institute for Regional Foreign Policies",
        "description": "Research institute focused on Israeli foreign policy and regional affairs. Useful for understanding international dimensions of the election.",
        "url": "https://mitvim.org.il/en/",
        "type": "think_tank",
        "language": "English / Hebrew",
        "reliability": "high",
        "bias_note": "center-left",
    },

    # ── POLLING & DATA ───────────────────────────────────────────────────────
    {
        "name": "Wikipedia – 2026 Israeli Legislative Election",
        "description": "Comprehensive, sourced overview of the election. Aggregates polling data from all major Israeli pollsters. Updated frequently with sources cited.",
        "url": "https://en.wikipedia.org/wiki/2026_Israeli_legislative_election",
        "type": "encyclopedia",
        "language": "English (also Hebrew)",
        "reliability": "high — community edited with cited sources",
        "bias_note": "neutral — aggregated",
    },
    {
        "name": "Israel Election Polls Aggregator (Wikipedia polling table)",
        "description": "Wikipedia maintains a continuously updated table of all polls by Israeli polling firms (Maariv, Channels 12/13, Panels Politics, Direct Polls, Smith). Best single place to track polling trends.",
        "url": "https://en.wikipedia.org/wiki/2026_Israeli_legislative_election#Opinion_polls",
        "type": "polling_aggregator",
        "language": "English",
        "reliability": "high — sourced from all Israeli pollsters",
        "bias_note": "neutral — aggregated data",
    },

    # ── POLITICIAN QUOTES ────────────────────────────────────────────────────
    {
        "name": "Hebrew Wikiquote — Israeli Politicians",
        "description": (
            "Hebrew-language Wikiquote repository of verified quotes by Israeli politicians. "
            "Community-edited with source citations. Useful for sourcing direct statements "
            "by MKs and ministers without relying on AI paraphrasing."
        ),
        "url": "https://he.wikiquote.org/wiki/",
        "type": "quotes_repository",
        "language": "Hebrew",
        "reliability": "high — community edited with citations",
        "bias_note": "neutral — direct quotes with source attribution",
        "usage_note": "Use for politician direct quotes. Always verify quote source link.",
    },

    # ── NON-PARTISAN PARLIAMENTARY DATA ──────────────────────────────────────
    {
        "name": "Open Knesset (כנסת פתוחה)",
        "description": (
            "Non-partisan, open-data project providing factual analysis of Israeli politics, "
            "parties, and politicians. Data is sourced daily from the Knesset's official OData API "
            "and made accessible via CSV pipelines. Covers MK profiles, faction membership, "
            "committee participation, and voting records."
        ),
        "url": "https://oknesset.org",
        "data_url": "https://production.oknesset.org/pipelines/data/",
        "type": "parliamentary_data",
        "language": "Hebrew / English (data files)",
        "reliability": "very high — sourced from official Knesset OData API",
        "bias_note": "neutral — non-partisan data project",
        "usage_note": "Primary source for MK profiles, faction data, and voting records in this app.",
    },

    # ── OFFICIAL PARTY REGISTRY ───────────────────────────────────────────────
    {
        "name": "Registrar of Political Parties (רשם המפלגות)",
        "description": (
            "Official Israeli government registry of all legally registered political parties. "
            "The authoritative source for party registration status, official party names, "
            "and founding documents. Maintained by the Ministry of Justice."
        ),
        "url": "https://www.gov.il/he/departments/topics/the_registrar_of_political_parties",
        "type": "official_government",
        "language": "Hebrew",
        "reliability": "authoritative",
        "bias_note": "neutral — official government registry",
        "usage_note": "Use to verify whether a party is officially registered. Especially relevant for new 2026 election parties.",
    },

    # ── STATISTICAL DATA (HIGHEST IMPORTANCE) ────────────────────────────────
    {
        "name": "Central Bureau of Statistics — Israel (CBS) | English",
        "description": (
            "Israel's official statistical authority. The single most important source for "
            "verified demographic, economic, and social data relevant to political analysis. "
            "Covers population data, household income, employment, housing prices, "
            "Arab-sector demographics, and voter turnout statistics. "
            "Highest-confidence factual data — not subject to editorial bias."
        ),
        "url": "https://www.cbs.gov.il/en",
        "type": "official_statistics",
        "language": "English",
        "reliability": "authoritative — highest confidence",
        "bias_note": "neutral — official statistical body",
        "usage_note": (
            "SUPER IMPORTANT. Use for any claim about population, economy, housing, or demographics. "
            "Always cite this source when presenting statistical figures in the Politics section."
        ),
    },
    {
        "name": "Central Bureau of Statistics — Israel (CBS) | Hebrew",
        "description": (
            "Hebrew version of Israel's official CBS. Contains additional datasets and reports "
            "not always available in English. Useful for detailed breakdowns of electoral "
            "district demographics, Arab and Haredi population data, and economic indicators."
        ),
        "url": "https://www.cbs.gov.il",
        "type": "official_statistics",
        "language": "Hebrew",
        "reliability": "authoritative — highest confidence",
        "bias_note": "neutral — official statistical body",
        "usage_note": (
            "SUPER IMPORTANT. Search in Hebrew for datasets not available in the English version. "
            "Primary reference for any demographic or economic data used in political context."
        ),
    },
]


# ── Service Functions ─────────────────────────────────────────────────────────

def get_election_overview() -> dict:
    """Return the 2026 election overview: date, context, blocs, key numbers."""
    return {
        **ELECTION_2026_OVERVIEW,
        "blocs_summary": ELECTION_2026_BLOCS,
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_parties_for_2026(bloc: str | None = None) -> list[dict]:
    """Return all parties expected to contest the 2026 election.

    Args:
        bloc: Optional filter — 'coalition', 'opposition', or 'arab_parties'.
    """
    parties = ELECTION_2026_PARTIES
    if bloc:
        parties = [p for p in parties if p.get("bloc") == bloc]
    return parties


def get_election_issues() -> list[dict]:
    """Return the key campaign issues for the 2026 election."""
    return ELECTION_2026_ISSUES


def get_election_blocs() -> dict:
    """Return current bloc projections with polling estimates."""
    return {
        "blocs": ELECTION_2026_BLOCS,
        "note": "Polling ranges as of June 2026. Figures vary by pollster and change frequently.",
        "majority_needed": 61,
        "poll_source": "Times of Israel aggregate, June 2026",
        "data_freshness": "2026-06-15",
    }


def get_election_sources() -> list[dict]:
    """Return the list of authoritative sources for Israeli election information.
    Intended to guide users to real sources instead of relying on AI.
    """
    return {
        "message": (
            "To inform yourself accurately about the Israeli elections, use these verified, "
            "authoritative sources. Do NOT rely on AI assistants for specific political facts — "
            "they can make mistakes. Primary source: bechirot.gov.il (official government authority)."
        ),
        "sources": ELECTION_2026_SOURCES,
        "data_freshness": "2026-06-15",
    }
