# generate_pdf.py
import os
import sys
import html
from datetime import datetime

# Import ReportLab modules
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# -------------------------------------------------------------------------
# NumberedCanvas for Header, Footer & Total Page Count
# -------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Cover page (page 1) has no header or footer
        if self._pageNumber > 1:
            # Header
            self.drawString(54, 745, "Israel News & Political Intelligence — Backend API Documentation")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 737, 612 - 54, 737)
            
            # Footer
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 54, 36, page_text)
            self.drawString(54, 36, "Confidential — For Internal Developer & Review Use Only")
            self.line(54, 48, 612 - 54, 48)
            
        self.restoreState()


# -------------------------------------------------------------------------
# Code Block Generator
# -------------------------------------------------------------------------
def make_code_block(code_text, styles):
    escaped = html.escape(code_text)
    # Preserve formatting for JSON
    escaped = escaped.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;').replace('  ', '&nbsp;&nbsp;')
    escaped = escaped.replace('\n', '<br/>')
    
    code_style = ParagraphStyle(
        'JSONCodeStyle',
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0F172A'),
    )
    p = Paragraph(escaped, code_style)
    t = Table([[p]], colWidths=[500])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BORDER', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    return t


# -------------------------------------------------------------------------
# API Schema Data Helper
# -------------------------------------------------------------------------
APIS = [
    # ------------------ SECTION 1: Health & Diagnostics ------------------
    {
        "section": "1. Health & Diagnostics",
        "method": "GET",
        "path": "/",
        "summary": "Root Health & Metadata",
        "logic": "Provides a simple check on root URL to verify FastAPI server is running. Returns service status, version, and the interactive FastAPI documentation path.",
        "input": "None",
        "output": '{\n  "status": "ok",\n  "version": "3.0.0",\n  "docs": "/docs"\n}'
    },
    {
        "section": "1. Health & Diagnostics",
        "method": "GET",
        "path": "/health",
        "summary": "System Liveness & Health",
        "logic": "Returns the system status alongside a UTC timestamp. Useful for Kubernetes liveness probes or automated uptime trackers.",
        "input": "None",
        "output": '{\n  "status": "healthy",\n  "timestamp": "2026-06-06T03:16:33.456Z"\n}'
    },
    {
        "section": "1. Health & Diagnostics",
        "method": "GET",
        "path": "/diagnostic/status",
        "summary": "External Services Status Check",
        "logic": "Inspects settings configuration environment variables for OpenAI, Gemini, Claude, and Perplexity keys. Reports whether each service API is configured or not configured.",
        "input": "None",
        "output": '{\n  "status": "ok",\n  "services": {\n    "openai": "configured",\n    "gemini": "not configured",\n    "claude": "not configured",\n    "perplexity": "configured",\n    "mongodb": "check via /political/mps or similar endpoint"\n  }\n}'
    },
    {
        "section": "1. Health & Diagnostics",
        "method": "GET",
        "path": "/diagnostic/openai/test",
        "summary": "OpenAI Connectivity Check",
        "logic": "Initializes an AsyncOpenAI client using the configured OPENAI_API_KEY. Sends a short test prompt 'Say ok' to model 'gpt-4o-mini' with max_tokens=5. Returns success metrics (model, tokens) or detailed troubleshooting steps on failure.",
        "input": "None",
        "output": '{\n  "status": "ok",\n  "message": "OpenAI API is reachable and key is valid",\n  "model": "gpt-4o-mini-2024-07-18",\n  "tokens_used": 5\n}'
    },
    {
        "section": "1. Health & Diagnostics",
        "method": "GET",
        "path": "/diagnostic/gemini/test",
        "summary": "Gemini Connectivity Check",
        "logic": "Configures google.generativeai with GEMINI_API_KEY, loads model 'gemini-pro', and triggers generate_content('Say ok'). Returns response text on success or instructions to generate an API key on failure.",
        "input": "None",
        "output": '{\n  "status": "ok",\n  "message": "Gemini API is reachable and key is valid",\n  "response": "ok"\n}'
    },

    # ------------------ SECTION 2: News Aggregation ------------------
    {
        "section": "2. News Aggregation",
        "method": "GET",
        "path": "/categories",
        "summary": "List News Categories",
        "logic": "Extracts and returns all active news categories supported by the application from the RSS_FEEDS map configuration keys.",
        "input": "None",
        "output": '{\n  "categories": [\n    "social", "economy", "defence", "education", "community",\n    "political", "positive", "sport", "culture", "environment",\n    "science", "international", "knesset", "arabic"\n  ],\n  "count": 14\n}'
    },
    {
        "section": "2. News Aggregation",
        "method": "GET",
        "path": "/sources",
        "summary": "List News Sources",
        "logic": "Retrieves preconfigured news sources. If detailed=true, lists sources with meta-information (language, country, default bias, baseline credibility score). If detailed=false, yields basic arrays of source names grouped by language.",
        "input": "?language=english&country=Israel&detailed=true\n(Parameters are optional. detailed defaults to false)",
        "output": '{\n  "sources": [\n    {\n      "name": "Times of Israel",\n      "url": "https://www.timesofisrael.com",\n      "feed_url": "https://www.timesofisrael.com/feed/",\n      "country": "Israel",\n      "language": "English",\n      "bias": "center",\n      "credibility": 0.85,\n      "category": "general"\n    }\n  ],\n  "total": 1\n}'
    },
    {
        "section": "2. News Aggregation",
        "method": "GET",
        "path": "/news/all",
        "summary": "Fetch All News Categories",
        "logic": "Concurrently fetches RSS feeds for all categories using asyncio.gather. Cleans HTML tags, filters opinion pieces and blocked sources, removes duplicate links, and applies category filters (e.g. excluding negative news for positive categories). Optional tiered AI analyses are run concurrently if with_analysis=true.",
        "input": "?limit=10&user_tier=free&with_analysis=false",
        "output": '{\n  "economy": {\n    "meta": {\n      "title": "Israeli News - Economy",\n      "description": "Top articles",\n      "link": "https://talmicahel.com"\n    },\n    "total": 1,\n    "articles": [\n      {\n        "title": "Bank of Israel maintains rate",\n        "link": "https://www.globes.co.il/news/article.1001",\n        "description": "The central bank decided to hold interest rates...",\n        "pub_date": "2026-06-06T07:00:00Z",\n        "source": "Globes",\n        "source_url": "https://globes.co.il"\n      }\n    ]\n  }\n}'
    },
    {
        "section": "2. News Aggregation",
        "method": "GET",
        "path": "/news/knesset",
        "summary": "Retrieve Knesset Bills & Fallbacks",
        "logic": "Tries to fetch Knesset bill legislation records from the official Knesset OData API. If unavailable, falls back to Google News RSS Kneseet queries. If that also fails, queries Wikipedia search APIs for summaries. If all fails, returns an empty array. Caches the response.",
        "input": "?limit=20",
        "output": '{\n  "source": "knesset.gov.il OData API",\n  "official_api_reachable": true,\n  "official_api_notice": "Connected to official Knesset OData API",\n  "total": 1,\n  "bills": [\n    {\n      "id": 20456,\n      "name": "State Budget Law 2026",\n      "name_hebrew": "חוק התקציב לשנת 2026",\n      "status": "Approved Third Reading",\n      "sub_type": "Government Bill",\n      "last_updated": "2026-06-05T18:30:00",\n      "initiator": "Ministry of Finance"\n    }\n  ]\n}'
    },
    {
        "section": "2. News Aggregation",
        "method": "GET",
        "path": "/news/{category}",
        "summary": "Fetch Specific Category News Feed",
        "logic": "Fetches RSS feeds for a given category (e.g. economy, defence). Parallel parses XML feeds, runs deduplication by URL, filters blocked sources and opinions. If with_analysis=true, initiates AI analysis matching the user tier (Free: Rule-based, Pro: GPT-4o-mini, Platinum: Ensemble). Uses MongoDB caching.",
        "input": "Path: /news/economy\nQuery Params: ?limit=20&exclude_negative=false&user_tier=pro&with_analysis=true",
        "output": '{\n  "meta": {\n    "title": "Israeli News - Economy",\n    "description": "Top articles from preconfigured feeds",\n    "link": "https://talmicahel.com"\n  },\n  "total": 1,\n  "articles": [\n    {\n      "title": "Israel Tech Exports Surge",\n      "link": "https://www.timesofisrael.com/tech-surge",\n      "description": "Exports of high-tech services rose by 12%...",\n      "pub_date": "2026-06-06T08:00:00Z",\n      "source": "Times of Israel",\n      "source_url": "https://timesofisrael.com",\n      "guid": "art-tech-123",\n      "sentiment": "positive",\n      "bias": "center",\n      "bias_score": 0.12,\n      "bias_types": ["source leaning"],\n      "bias_category": "Objective Reporting",\n      "credibility_score": 0.85,\n      "credibility_label": "verified",\n      "fact_check_score": 0.77,\n      "summary_hebrew": "יצוא ההייטק הישראלי עלה ב-12 אחוזים.",\n      "topics": ["economy", "technology"],\n      "claims": ["High-tech services exports rose by 12%"],\n      "factual_points": ["Central Bureau of Statistics released trade figures today"]\n    }\n  ]\n}'
    },

    # ------------------ SECTION 3: AI Analysis & Crowdsourcing ------------------
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/analyze",
        "summary": "Analyze Article Bias & Sentiment",
        "logic": "Analyzes article bias, sentiment, and credibility. Tiered strategy applied:\n- free: Rule-based analysis checking keyword list and seed dictionary leanings.\n- pro: Calls GPT-4o-mini with structured JSON parsing prompts. Falls back to rule-based on failure.\n- platinum: Queries GPT-4o-mini, Perplexity (pplx-7b-online), and Gemini, then merges values via consensus averages.",
        "input": '{\n  "guid": "art-001",\n  "title": "Knesset approves new budget",\n  "description": "The Israeli parliament approved the 2025 state budget after weeks of negotiations.",\n  "source": "Haaretz",\n  "source_url": "https://haaretz.com"\n}\nQuery: ?user_tier=pro',
        "output": '{\n  "guid": "art-001",\n  "sentiment": "neutral",\n  "bias": "left",\n  "bias_score": 0.45,\n  "bias_types": ["source leaning", "editorial framing"],\n  "bias_category": "Source Bias",\n  "bias_score_explanation": "Source Haaretz is registered as left-leaning.",\n  "credibility_score": 0.82,\n  "credibility_label": "likely credible",\n  "fact_check_score": 0.74,\n  "summary_hebrew": "הכנסת אישרה את תקציב המדינה לשנת 2025.",\n  "topics": ["politics", "economy"],\n  "claims": ["Budget approved after weeks of negotiations"],\n  "factual_points": ["Knesset plenary voted on the bill"],\n  "claim_explanation": "Negotiation timeline is framed as an assertion.",\n  "bias_explanation": "Article reflects reporting with moderate left-wing editorial frame."\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/analyze/batch",
        "summary": "Batch Analyze Articles",
        "logic": "Accepts a list of up to 20 articles and executes analyze_article concurrently using asyncio.gather.",
        "input": '{\n  "articles": [\n    {\n      "guid": "art-001",\n      "title": "Title 1",\n      "description": "Description 1"\n    }\n  ]\n}\nQuery: ?user_tier=free',
        "output": '[\n  {\n    "guid": "art-001",\n    "sentiment": "neutral",\n    "bias": "unknown",\n    "bias_score": 0.05,\n    "bias_types": ["neutral framing"],\n    "bias_category": "Objective Reporting",\n    "bias_score_explanation": "Baseline score",\n    "credibility_score": 0.5,\n    "credibility_label": "needs review",\n    "fact_check_score": 0.45,\n    "summary_hebrew": "[סיכום אוטומטי] Title 1",\n    "topics": ["general"],\n    "claims": ["Title 1"],\n    "factual_points": ["Title 1"],\n    "claim_explanation": "Baseline",\n    "bias_explanation": "No lean detected"\n  }\n]'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "GET",
        "path": "/ai/source-bias",
        "summary": "Get Single Source Seed Bias",
        "logic": "Returns the default baseline bias alignment and credibility score for a source from the pre-seeded local lookup table.",
        "input": "?source=Haaretz&source_url=https://haaretz.com",
        "output": '{\n  "source_name": "Haaretz",\n  "bias": "left",\n  "credibility_score": 0.82,\n  "bias_label": "⬅️ Left"\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "GET",
        "path": "/ai/source-bias/all",
        "summary": "Get Full Baseline Bias Table",
        "logic": "Compiles all preconfigured news sources in ISRAELI_SOURCES, maps their seed bias and credibility tables, and yields a complete sorted dataset.",
        "input": "None",
        "output": '{\n  "total": 13,\n  "sources": [\n    {\n      "source_name": "Arutz Sheva",\n      "bias": "right",\n      "credibility_score": 0.65,\n      "bias_label": "➡️ Right"\n    }\n  ]\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/articles/{article_id}/vote/bias",
        "summary": "Submit Crowdsourced Article Bias Vote",
        "logic": "Records a user's assessment of an article's bias ('left', 'center', 'right', 'unclear') with their confidence score in the MongoDB 'bias_votes' collection. Real-time consensus computes weight bias using weights: free=1.0, pro=1.5, platinum=2.0 once 5+ user votes are registered; otherwise trusts the AI analysis.",
        "input": "Path: /ai/articles/art-123/vote/bias\nQuery: ?user_id=usr-555&user_tier=pro\nBody:\n{\n  \"bias_assessment\": \"left\",\n  \"confidence\": 0.85,\n  \"user_notes\": \"Highly emotive wording regarding budget deficits.\"\n}",
        "output": '{\n  "status": "recorded",\n  "vote_id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "article_id": "art-123",\n  "recorded_at": "2026-06-06T09:00:00Z"\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/sources/{source_name}/vote/credibility",
        "summary": "Vote on News Source Credibility",
        "logic": "Submits a rating ('very_low', 'low', 'medium', 'high', 'very_high') mapping to credibility scores (0.1 to 0.95). Stores vote in MongoDB 'credibility_votes' collection. Updates user consensus credibility score on 5+ user submissions.",
        "input": "Path: /ai/sources/Haaretz/vote/credibility\nQuery: ?user_id=usr-555&user_tier=pro\nBody:\n{\n  \"credibility_level\": \"high\",\n  \"evidence\": \"Consistent verification processes and standard reporting practices.\"\n}",
        "output": '{\n  "status": "recorded",\n  "vote_id": "64f1a2b3c4d5e6f7a8b9c0d2",\n  "source_name": "Haaretz",\n  "recorded_at": "2026-06-06T09:01:00Z"\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/articles/{article_id}/flag",
        "summary": "Flag Article for Moderation",
        "logic": "Records a moderation warning flag ('misinformation', 'propaganda', 'biased', 'unreliable_source') in MongoDB 'article_flags' with status 'pending' for review by moderators.",
        "input": "Path: /ai/articles/art-123/flag\nQuery: ?user_id=usr-555\nBody:\n{\n  \"reason\": \"misinformation\",\n  \"details\": \"The GDP figures quoted clash directly with official Central Bureau of Statistics bulletins.\"\n}",
        "output": '{\n  "status": "flagged",\n  "flag_id": "64f1a2b3c4d5e6f7a8b9c0d3",\n  "article_id": "art-123",\n  "reason": "misinformation",\n  "message": "Thank you for helping us maintain quality. Our team will review this."\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "GET",
        "path": "/ai/articles/{article_id}/votes",
        "summary": "Get Article Voting Stats & Flags",
        "logic": "Queries database bias votes and flags for the requested article, compiling averages and grouping flags by reason (user IDs are masked for privacy).",
        "input": "Path: /ai/articles/art-123/votes",
        "output": '{\n  "article_id": "art-123",\n  "bias_votes_count": 2,\n  "flags_count": 1,\n  "votes": {\n    "bias_votes": [\n      { "bias_assessment": "left", "confidence": 0.85, "helpful_count": 0 }\n    ],\n    "flag_count": 1,\n    "flags_by_reason": { "misinformation": 1 }\n  }\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "POST",
        "path": "/ai/votes/{vote_id}/helpful",
        "summary": "Mark Vote as Helpful (Upvote)",
        "logic": "Increments helpful_count of a specific bias or credibility vote by 1 in MongoDB. Surfaces high-quality community feedback.",
        "input": "Path: /ai/votes/64f1a2b3c4d5e6f7a8b9c0d1/helpful\nQuery: ?vote_type=bias",
        "output": '{\n  "status": "upvoted",\n  "vote_id": "64f1a2b3c4d5e6f7a8b9c0d1"\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "GET",
        "path": "/ai/user/{user_id}/vote-history",
        "summary": "Get User Voting History & Reputation",
        "logic": "Queries bias_votes, credibility_votes, and article_flags collections to return total counts and the last 5 records of user submissions.",
        "input": "Path: /ai/user/usr-555/vote-history?limit=10",
        "output": '{\n  "user_id": "usr-555",\n  "reputation": {\n    "bias_votes": 12,\n    "credibility_votes": 4,\n    "flags_submitted": 2\n  },\n  "recent_activity": {\n    "bias_votes": [],\n    "credibility_votes": [],\n    "flags": []\n  }\n}'
    },
    {
        "section": "3. AI Analysis & Voting",
        "method": "GET",
        "path": "/ai/votes/leaderboard",
        "summary": "Voter Leaderboard",
        "logic": "Aggregates votes in MongoDB grouped by user_id. Summarizes total votes and total helpful upvotes received, sorting top users descending.",
        "input": "?limit=10",
        "output": '{\n  "leaderboard": [\n    {\n      "_id": "usr-999",\n      "total_votes": 150,\n      "helpful_votes": 340\n    }\n  ],\n  "description": "Top voters by helpful votes received"\n}'
    },

    # ------------------ SECTION 4: Political Intelligence ------------------
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/sync",
        "summary": "Sync Knesset API Core Objects",
        "logic": "Fetches and upserts active 25th Knesset members (KNS_PersonToPosition), political factions (KNS_Faction), and committees (KNS_Committee) directly from official Knesset OData endpoints into MongoDB. Computes standard wing leanings (left/center/right).",
        "input": "None",
        "output": '{\n  "synced": {\n    "mps": 120,\n    "parties": 10,\n    "committees": 18\n  }\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/mps",
        "summary": "List Members of Knesset (MKs)",
        "logic": "Queries active Members of Knesset from MongoDB 'mps' collection. Allows filtering by political party faction name.",
        "input": "?party_name=Likud",
        "output": '{\n  "total": 32,\n  "mps": [\n    {\n      "knesset_id": 200,\n      "name": "Benjamin Netanyahu",\n      "name_hebrew": "בנימין נתניהו",\n      "role": "Prime Minister",\n      "is_active": true\n    }\n  ]\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/mps/{mp_id}",
        "summary": "Get MP Profile with Quotes & Actions",
        "logic": "Fetches MP core profile by Object ID, then queries the database to join up to 50 quote statements (mp_quotes) and 50 logged votes or actions (mp_actions).",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1",
        "output": '{\n  "id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "name": "Benjamin Netanyahu",\n  "role": "Prime Minister",\n  "consistency_score": 0.85,\n  "quotes": [],\n  "actions": []\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/mps/{mp_id}/quotes",
        "summary": "Add Statement / Quote for MP",
        "logic": "Inserts an MP quote record in 'mp_quotes' collection containing the statement text, date, source URL, and category topic.",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/quotes\nBody:\n{\n  \"quote\": \"We will pass this economic reform package immediately.\",\n  \"context\": \"Press conference in Tel Aviv\",\n  \"source_url\": \"https://www.ynetnews.com/art-econ\",\n  \"topic\": \"economy\",\n  \"date\": \"2026-06-01\"\n}",
        "output": '{\n  "mp_id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "quote": "We will pass this economic reform package immediately.",\n  "topic": "economy",\n  "id": "64f1a2b3c4d5e6f7a8b9c0d9"\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/mps/{mp_id}/actions",
        "summary": "Add Action / Vote Record for MP",
        "logic": "Records a legislative vote, speech, or bill initiation in MongoDB 'mp_actions' matching the MP.",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/actions\nBody:\n{\n  \"action\": \"Voted YES on Economic Deregulation Bill\",\n  \"action_type\": \"vote\",\n  \"topic\": \"economy\",\n  \"source_url\": \"https://knesset.gov.il/vote-101\",\n  \"date\": \"2026-06-05\"\n}",
        "output": '{\n  "mp_id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "action": "Voted YES on Economic Deregulation Bill",\n  "topic": "economy",\n  "id": "64f1a2b3c4d5e6f7a8b9c0d0"\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/mps/{mp_id}/contradictions/scan",
        "summary": "Scan MP for Statement Contradictions",
        "logic": "Compares all stored quotes and actions for an MP matching identical topics. Triggers GPT-4o-mini to search logical contradictions (or runs rule-based keyword opposition checks as fallback). Records findings in MongoDB and re-calculates MP's reliability 'consistency_score'.",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/contradictions/scan",
        "output": '{\n  "mp_id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "new_contradictions_found": 0,\n  "contradictions": []\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/mps/{mp_id}/contradictions",
        "summary": "Get Recorded MP Contradictions",
        "logic": "Retrieves quote-vs-action contradiction documents stored for the requested MP, sorted by detection date.",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/contradictions",
        "output": '{\n  "mp_id": "64f1a2b3c4d5e6f7a8b9c0d1",\n  "total": 1,\n  "contradictions": [\n    {\n      "quote_id": "64f1a2b3...",\n      "action_id": "64f1a2b4...",\n      "explanation": "MP voted against the economic package after declaring support in public.",\n      "severity": "high",\n      "topic": "economy",\n      "detected_at": "2026-06-06T09:10:00Z"\n    }\n  ]\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/parties",
        "summary": "List Parties & Factions",
        "logic": "Returns all registered political parties from MongoDB 'parties' collection sorted by Knesset seat count.",
        "input": "None",
        "output": '{\n  "total": 3,\n  "parties": [\n    { "name": "Likud", "seats": 32, "wing": "right" },\n    { "name": "Yesh Atid", "seats": 24, "wing": "center" },\n    { "name": "Labor", "seats": 4, "wing": "left" }\n  ]\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/parties/{party_id}",
        "summary": "Get Party Details & Members List",
        "logic": "Retrieves party document metadata and lists active Knesset members matching this party ID from the database.",
        "input": "Path: /political/parties/64f1a2b3c4d5e6f7a8b9c0d2",
        "output": '{\n  "id": "64f1a2b3c4d5e6f7a8b9c0d2",\n  "name": "Likud",\n  "seats": 32,\n  "members": [\n    { "name": "Benjamin Netanyahu", "role": "Prime Minister" }\n  ]\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/committees",
        "summary": "List Knesset Committees",
        "logic": "Queries Knesset standing committees stored in MongoDB, sorting alphabetically.",
        "input": "None",
        "output": '{\n  "total": 2,\n  "committees": [\n    { "committee_id": 1, "name": "Finance Committee", "name_hebrew": "ועדת הכספים" }\n  ]\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/bills/sync",
        "summary": "Sync Recent Knesset Bills",
        "logic": "Fetches recent bills from Knesset API, parses core fields (status, initiators, committee, summaries), and upserts them into MongoDB 'knesset_bills'.",
        "input": "?limit=50",
        "output": '{\n  "synced": 50\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/bills/health",
        "summary": "Check Official Knesset API Health",
        "logic": "Tests direct connectivity and response latency for the official Knesset OData endpoint, providing a quick debugging ping.",
        "input": "None",
        "output": '{\n  "official_api_reachable": true,\n  "notice": "Knesset API reachable"\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/bills/{bill_id}/sync-votes",
        "summary": "Sync Official Votes on a Bill",
        "logic": "Queries the official Knesset vote OData collections matching this bill. Iterates through records, resolves Knesset person ID to internal MP profiles, and inserts votes in MongoDB 'bill_vote_records'.",
        "input": "Path: /political/bills/20123/sync-votes",
        "output": '{\n  "bill_id": "20123",\n  "mp_votes_synced": 120\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/bills",
        "summary": "List Synced Knesset Bills",
        "logic": "Queries local 'knesset_bills' sorted by last updated date, returning summaries. Displays reachability notice of Knesset API.",
        "input": "?limit=20",
        "output": '{\n  "total": 1,\n  "bills": [\n    { "bill_id": "20123", "name": "State Budget Law", "status": "Approved" }\n  ],\n  "official_api_reachable": true,\n  "official_api_notice": "Connected to official Knesset OData API"\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/bills/{bill_id}",
        "summary": "Get Synced Bill Details & Summaries",
        "logic": "Resolves bill by ID. If summary exists but no AI summary is generated, invokes GPT-4o-mini to compose a summary in Hebrew. Joins user community votes tally and official MK vote tallies.",
        "input": "Path: /political/bills/20123",
        "output": '{\n  "bill_id": "20123",\n  "name": "State Budget Law",\n  "summary": "This bill defines state revenues...",\n  "ai_summary": "חוק התקציב לשנת 2026...",\n  "community_tally": { "total_votes": 10, "support": 8, "oppose": 2, "support_pct": 80.0 },\n  "official_vote_summary": { "total": 120, "yes": 64, "no": 56, "abstain": 0, "absent": 0, "other": 0 }\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/bills/{bill_id}/votes",
        "summary": "Get Synced MK Vote Records on Bill",
        "logic": "Retrieves official vote records associated with a bill from 'bill_vote_records', returning vote values (yes/no/abstain) for each MK.",
        "input": "Path: /political/bills/20123/votes",
        "output": '[\n  {\n    "bill_id": "20123",\n    "mp_name": "Benjamin Netanyahu",\n    "party": "Likud",\n    "vote": "yes",\n    "vote_date": "2026-06-05T18:00:00"\n  }\n]'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/mps/{mp_id}/votes",
        "summary": "Get Official Voting History for MK",
        "logic": "Queries 'bill_vote_records' matching the MP object ID or Kneseet person ID. Returns chronological voting history.",
        "input": "Path: /political/mps/64f1a2b3c4d5e6f7a8b9c0d1/votes",
        "output": '[\n  {\n    "bill_id": "20123",\n    "mp_name": "Benjamin Netanyahu",\n    "vote": "yes",\n    "vote_date": "2026-06-05T18:00:00"\n  }\n]'
    },
    {
        "section": "4. Political Intelligence",
        "method": "POST",
        "path": "/political/bills/{bill_id}/vote",
        "summary": "Submit Referendum Vote on Bill",
        "logic": "Allows system users to vote on a bill (referendum model). Saves vote in MongoDB 'bill_votes' collection and returns the updated community tally.",
        "input": "Path: /political/bills/20123/vote\nBody:\n{\n  \"support\": true\n}",
        "output": '{\n  "bill_id": "20123",\n  "total_votes": 15,\n  "support": 12,\n  "oppose": 3,\n  "support_pct": 80.0\n}'
    },
    {
        "section": "4. Political Intelligence",
        "method": "GET",
        "path": "/political/bills/{bill_id}/tally",
        "summary": "Get Community Vote Tally",
        "logic": "Counts support and oppose votes submitted by community members for a bill.",
        "input": "Path: /political/bills/20123/tally",
        "output": '{\n  "bill_id": "20123",\n  "total_votes": 15,\n  "support": 12,\n  "oppose": 3,\n  "support_pct": 80.0\n}'
    },

    # ------------------ SECTION 5: Smart Correlation Engine ------------------
    {
        "section": "5. Smart Correlation Engine",
        "method": "POST",
        "path": "/correlation/cluster",
        "summary": "Cluster Articles by Theme",
        "logic": "Groups input articles by theme and exposes contradictions.\n- free: Heuristic Jaccard overlap of extracted TF-IDF keywords. Flags contradictions if sources use opposing sentiment keywords (e.g. success vs crisis).\n- pro: Sends article titles/sources to GPT-4o-mini, yielding semantic clusters and inconsistencies via structured JSON.",
        "input": '{\n  "articles": [\n    {\n      "guid": "a1",\n      "title": "Bank of Israel hikes interest rates to combat inflation.",\n      "source": "Globes"\n    },\n    {\n      "guid": "a2",\n      "title": "Shekel strengthens following BoI interest rate hike.",\n      "source": "Haaretz"\n    }\n  ],\n  "use_ai": false\n}',
        "output": '{\n  "total_articles": 2,\n  "total_clusters": 1,\n  "clusters_with_inconsistency": 0,\n  "clusters": [\n    {\n      "theme": "rates, shekel, interest",\n      "article_count": 2,\n      "articles": [\n        { "guid": "a1", "title": "Bank of Israel..." }\n        { "guid": "a2", "title": "Shekel strengthens..." }\n      ],\n      "inconsistency": null,\n      "method": "rule-based"\n    }\n  ]\n}'
    },
    {
        "section": "5. Smart Correlation Engine",
        "method": "GET",
        "path": "/correlation/cluster/live",
        "summary": "Cluster Live News Feeds",
        "logic": "Fetches live news from all RSS categories concurrently, flattens articles, clusters them dynamically via keywords or AI, and sorts clusters prioritizing conflicts.",
        "input": "?limit=15&use_ai=true",
        "output": '{\n  "total_articles": 45,\n  "total_clusters": 12,\n  "clusters_with_inconsistency": 1,\n  "clusters": []\n}'
    },
    {
        "section": "5. Smart Correlation Engine",
        "method": "POST",
        "path": "/correlation/cross-reference",
        "summary": "Match News to Knesset Bills",
        "logic": "Cross-references input articles with input bills. Analyzes keyword overlap Jaccard scores. Returns matches with relevance_score values.",
        "input": '{\n  "articles": [\n    { "title": "New education reform passes first reading" }\n  ],\n  "bills": [\n    { "name": "Education Reform Act 2025", "name_hebrew": "חוק רפורמת החינוך" }\n  ]\n}',
        "output": '{\n  "total_articles": 1,\n  "articles_with_bill_matches": 1,\n  "matches": [\n    {\n      "article_title": "New education reform passes first reading",\n      "related_bills": [\n        {\n          "name": "Education Reform Act 2025",\n          "relevance_score": 0.25\n        }\n      ]\n    }\n  ]\n}'
    },
    {
        "section": "5. Smart Correlation Engine",
        "method": "GET",
        "path": "/correlation/cross-reference/live",
        "summary": "Cross-reference Live News & Bills",
        "logic": "Fetches live news articles and Kneseet bills concurrently. Compares and indexes matches automatically.",
        "input": "?limit=15",
        "output": '{\n  "total_articles": 30,\n  "total_bills": 20,\n  "articles_with_bill_matches": 2,\n  "matches": []\n}'
    },

    # ------------------ SECTION 6: AI Insights & Trends ------------------
    {
        "section": "6. AI Insights & Trends",
        "method": "GET",
        "path": "/insights/trends",
        "summary": "Detect Global Trending Topics",
        "logic": "Aggregates titles from live news. Filters common stop words. Computes keyword frequencies. If use_ai=true, triggers GPT-4o-mini for semantic trends synthesis.",
        "input": "?limit=10&use_ai=false",
        "output": '{\n  "total_articles_analyzed": 120,\n  "use_ai": false,\n  "trends": [\n    { "keyword": "budget", "count": 14, "sample_headlines": [] }\n  ]\n}'
    },
    {
        "section": "6. AI Insights & Trends",
        "method": "GET",
        "path": "/insights/all",
        "summary": "Generate Insights for All Categories",
        "logic": "Concurrently fetches news and generates category insights. Compiles global trends from the combined keywords list.",
        "input": "?limit=10&use_ai=true",
        "output": '{\n  "economy": {\n    "category": "economy",\n    "insight_hebrew": "מגמת הכלכלה נשארת יציבה למרות..."\n  },\n  "global_trends": [\n    { "keyword": "budget", "total_count": 25 }\n  ]\n}'
    },
    {
        "section": "6. AI Insights & Trends",
        "method": "GET",
        "path": "/insights/{category}",
        "summary": "Generate Category Insights",
        "logic": "Extracts trending keywords for category articles. Generates a 3-sentence summary insight in Hebrew (using GPT-4o-mini if use_ai=true, or rule-based English descriptors as fallback). Responses are cached.",
        "input": "Path: /insights/economy\nQuery: ?limit=20&use_ai=true",
        "output": '{\n  "category": "economy",\n  "article_count": 20,\n  "insight_hebrew": "נרשמת עלייה בפעילות ההייטק לצד יציבות במדד המחירים לצרכן. בנק ישראל עשוי להשאיר את הריבית ללא שינוי ברבעון הקרוב.",\n  "trends": [\n    { "keyword": "inflation", "count": 6 }\n  ],\n  "generated_at": "2026-06-06T09:12:00Z"\n}'
    },
    {
        "section": "6. AI Insights & Trends",
        "method": "GET",
        "path": "/insights/subscription/summary/{period}",
        "summary": "Generate Subscription Digest",
        "logic": "Assembles a lightweight text digest of the top three headlines from each news category. Period must be 'weekly' or 'monthly'. Designed for newsletter dispatch.",
        "input": "Path: /insights/subscription/summary/weekly?limit=5",
        "output": '{\n  "period": "weekly",\n  "generated_at": "2026-06-06T09:12:00Z",\n  "total_headlines": 18,\n  "summary": "Economy: BoI rates steady | Tech investment rises\\nPolitics: Knesset budget debate..."\n}'
    },

    # ------------------ SECTION 7: AI Q&A Engine ------------------
    {
        "section": "7. AI Q&A Box",
        "method": "POST",
        "path": "/qa/ask",
        "summary": "Ask GPT-4o with News Context",
        "logic": "Accepts a natural language query. Formats context using recent articles matching the requested category. Configures a system prompt directing GPT-4o to act as a factual, neutral Israeli analyst. Caches responses.",
        "input": '{\n  "question": "What is the status of the education budget?",\n  "category": "education",\n  "use_context": true,\n  "model": "gpt-4o"\n}',
        "output": '{\n  "answer": "According to Ynet and Kan news, the education budget is projected to increase by 4% to fund school infrastructure...",\n  "model": "gpt-4o",\n  "tokens_used": 412,\n  "cached": false\n}'
    },
    {
        "section": "7. AI Q&A Box",
        "method": "POST",
        "path": "/qa/ask/stream",
        "summary": "Stream Q&A Responses (SSE)",
        "logic": "Accepts Q&A body, constructs system contexts, and establishes a Server-Sent Events (SSE) stream (text/event-stream) streaming token increments.",
        "input": '{\n  "question": "Explain Knesset budget updates",\n  "model": "gpt-4o-mini"\n}',
        "output": "data: According<br/>data: to recent<br/>data: updates...<br/>data: [DONE]"
    },
    {
        "section": "7. AI Q&A Box",
        "method": "POST",
        "path": "/qa/ask/ithy",
        "summary": "Ask ITHY Simulated Multi-Perspective AI",
        "logic": "Simulates the ITHY.ai web-search multi-perspective engine. Invokes GPT-4o with instructions to search angles, detail conflicting opinions, and build syntheses.",
        "input": '{\n  "question": "What are the arguments surrounding the shekel stability?"\n}',
        "output": '{\n  "answer": "Analysis from three key perspectives:\\n1. Exporters claim shekel strength hurts competitiveness...\\n2. Central bank states shekel strength curbs imported inflation...\\n3. Retailers cite benefits of cheaper import pricing...",\n  "source": "ithy-simulated",\n  "cached": false\n}'
    },
    {
        "section": "7. AI Q&A Box",
        "method": "POST",
        "path": "/qa/ask/dual",
        "summary": "Compare GPT vs ITHY Side-by-Side",
        "logic": "Triggers ask_gpt and ask_ithy concurrently. Combines answers, and prompts gpt-4o-mini with a summarization prompt to produce a one-sentence comparative differential note.",
        "input": '{\n  "question": "Is the government coalition stable?",\n  "model": "gpt-4o"\n}',
        "output": '{\n  "question": "Is the government coalition stable?",\n  "gpt": {\n    "answer": "The coalition holds a majority but faces policy tension...",\n    "model": "gpt-4o"\n  },\n  "ithy": {\n    "answer": "From political analysts, stability is viewed through party cohesion..."\n  },\n  "comparison_note": "GPT highlights specific policy issues while ITHY emphasizes general party cohesion."\n}'
    },
    {
        "section": "7. AI Q&A Box",
        "method": "GET",
        "path": "/qa/ask",
        "summary": "Quick GET Q&A Endpoint",
        "logic": "GET query endpoint wrapper. Resolves recent database articles as context, then calls gpt-4o-mini.",
        "input": "?q=What+happened+in+Knesset+today",
        "output": '{\n  "answer": "Today, the Knesset debated educational funding bills...",\n  "model": "gpt-4o-mini",\n  "tokens_used": 240,\n  "cached": false\n}'
    },

    # ------------------ SECTION 8: Social Media Scraping ------------------
    {
        "section": "8. Social Media Integration",
        "method": "GET",
        "path": "/social/twitter/search",
        "summary": "Search Twitter / X via twscrape",
        "logic": "Invokes twscrape query parser. If israeli_only=true, builds query appending preconfigured Israeli accounts and hashtags. Maps responses to NewsArticle schema. Returns 503 if twscrape is not installed.",
        "input": "?query=Israel+economy&limit=10&israeli_only=true",
        "output": '{\n  "query": "Israel economy",\n  "full_query": "(Israel economy) (from:Jerusalem_Post OR from:TimesofIsrael) lang:en",\n  "count": 1,\n  "tweets": [\n    {\n      "title": "Tweet by @Jerusalem_Post",\n      "link": "https://twitter.com/Jerusalem_Post/status/12999",\n      "description": "Israeli economy expands 3% in Q1 according to official statistics.",\n      "pub_date": "2026-06-06T08:00:00Z",\n      "source": "Twitter / X",\n      "source_url": "https://twitter.com/Jerusalem_Post",\n      "guid": "12999"\n    }\n  ]\n}'
    },
    {
        "section": "8. Social Media Integration",
        "method": "GET",
        "path": "/social/twitter/user/{username}",
        "summary": "Get User Tweets via twscrape",
        "logic": "Resolves Twitter username login ID to numeric Twitter user ID using twscrape. Fetches user's recent tweets.",
        "input": "Path: /social/twitter/user/TimesofIsrael?limit=5",
        "output": '{\n  "username": "TimesofIsrael",\n  "count": 1,\n  "tweets": []\n}'
    },
    {
        "section": "8. Social Media Integration",
        "method": "GET",
        "path": "/social/twitter/israeli-accounts",
        "summary": "Get Israeli Account Tweets",
        "logic": "Iterates parallel calls via asyncio.gather fetching recent tweets from all 10 preconfigured active accounts.",
        "input": "?limit=5",
        "output": '{\n  "accounts": ["Jerusalem_Post", "TimesofIsrael", "haaretzcom", ...],\n  "data": {\n    "TimesofIsrael": []\n  }\n}'
    }
]


# -------------------------------------------------------------------------
# Build Document
# -------------------------------------------------------------------------
def generate_pdf():
    pdf_filename = "api_documentation.pdf"
    
    # Page structure setup
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'CoverTitleStyle',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitleStyle',
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#475569'),
        alignment=1, # Center
        spaceAfter=40
    )
    
    meta_style = ParagraphStyle(
        'CoverMetaStyle',
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        alignment=1, # Center
    )
    
    h1_style = ParagraphStyle(
        'Header1Style',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=22,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2Style',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'CustomBodyStyle',
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#475569'),
    )

    story = []

    # ------------------ COVER PAGE ------------------
    story.append(Spacer(1, 150))
    story.append(Paragraph("Israel News & Political Intelligence", title_style))
    story.append(Paragraph("Comprehensive Backend API Documentation & Logic Manual", subtitle_style))
    
    # Colored accent line
    accent_bar = Table([[""]], colWidths=[504], rowHeights=[4])
    accent_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#3B82F6')),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(accent_bar)
    story.append(Spacer(1, 40))
    
    # Cover Metadata
    story.append(Paragraph(f"<b>Generation Date:</b> {datetime.now().strftime('%B %d, %Y')}", meta_style))
    story.append(Paragraph("<b>Version:</b> 3.0.0", meta_style))
    story.append(Paragraph("<b>Framework:</b> FastAPI (Python) & MongoDB & Redis Cache", meta_style))
    story.append(Paragraph("<b>Author:</b> Antigravity AI Assistant & Developer Team", meta_style))
    story.append(Spacer(1, 150))
    story.append(Paragraph("<i>This document outlines the business logic, request schema configurations, and sample responses for all routing layers.</i>", meta_style))
    story.append(PageBreak())

    # ------------------ INTRODUCTORY SYSTEM OVERVIEW ------------------
    story.append(Paragraph("System Architecture & Implementation Overview", h1_style))
    intro_p1 = (
        "The Israel News & Political Intelligence API is a highly modular, real-time data aggregation "
        "and analytical engine. Built on <b>FastAPI</b>, it handles high-throughput scraping, concurrent RSS "
        "parsing, AI bias evaluations, Knesset intelligence syncs, and Q&A interactions."
    )
    intro_p2 = (
        "<b>Key Infrastructure Pillars:</b><br/>"
        "• <b>FastAPI & Pydantic:</b> Strictly validates request schemas and enforces response typing for client guarantees.<br/>"
        "• <b>MongoDB Storage:</b> Persists crawled news categories, user crowdsourced votes, MP profiles, and Knesset voting tally indexes.<br/>"
        "• <b>Caching Layers:</b> Key endpoints implement dynamic TTL cache locks (news, Knesset bills) in Redis/Memory to prevent rate limits.<br/>"
        "• <b>Multi-Model AI Integration:</b> Implements a tiered analysis structure. Free tiers fall back to token/regex rule baselines; Pro uses "
        "GPT-4o-mini; Platinum activates an ensemble of Perplexity, Gemini, and OpenAI models with weighted average consensus."
    )
    story.append(Paragraph(intro_p1, body_style))
    story.append(Paragraph(intro_p2, body_style))
    story.append(Spacer(1, 15))

    # Keep track of active sections
    current_section = None

    # Iterate and build flowables for each API
    for api in APIS:
        # Check section change
        if api["section"] != current_section:
            current_section = api["section"]
            story.append(Spacer(1, 10))
            story.append(Paragraph(current_section, h1_style))
            story.append(Spacer(1, 5))
        
        # Build API header
        # Method badge styling
        method = api["method"].upper()
        if method == "GET":
            method_color = "#10B981"  # Emerald Green
        elif method == "POST":
            method_color = "#3B82F6"  # Blue
        elif method == "PUT":
            method_color = "#F59E0B"  # Amber
        else:
            method_color = "#EF4444"  # Red
            
        header_text = f"<b><font color='{method_color}'>{method}</font>&nbsp;&nbsp;&nbsp;&nbsp;{api['path']}</b>"
        api_header = Paragraph(f"{header_text} — {api['summary']}", h2_style)
        
        # Backend Logic Paragraph
        logic_p = Paragraph(f"<b>Backend Logic:</b> {api['logic']}", body_style)
        
        # Details table containing parameters
        details_data = [
            [Paragraph("<b>Sample Input / Params:</b>", label_style), Paragraph(html.escape(api["input"]).replace('\n', '<br/>'), body_style)]
        ]
        details_table = Table(details_data, colWidths=[130, 370])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        # Output block
        output_code = make_code_block(api["output"], styles)
        
        # Group elements for this endpoint together to prevent mid-endpoint page breaks
        endpoint_elements = [
            api_header,
            logic_p,
            details_table,
            Spacer(1, 4),
            Paragraph("<b>Sample Output / Response:</b>", label_style),
            Spacer(1, 2),
            output_code,
            Spacer(1, 15)
        ]
        story.append(KeepTogether(endpoint_elements))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF generation completed successfully.")

if __name__ == "__main__":
    generate_pdf()
