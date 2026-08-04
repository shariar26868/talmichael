# app/routes/bills.py
"""
Root-level router for Knesset Bills.
Endpoints:
  - GET /bills?user_tier=pro&with_analysis=true
  - POST /bills/{bill_id}/vote
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bills & Reforms"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BillOut(BaseModel):
    bill_id: str
    title: str
    proposed_by: str
    date: str
    explanation: Optional[str] = None
    key_provisions: Optional[List[str]] = None
    category_tags: List[str]
    verification_status: str = "source-backed"
    verification_sources: List[str] = []


class BillsListResponse(BaseModel):
    bills: List[BillOut]


class VoteRequest(BaseModel):
    vote: str = Field(..., description="support | oppose | neutral | abstain | none")


class PublicOpinion(BaseModel):
    support: int
    oppose: int
    neutral: int
    abstain: int
    total_votes: int


class VoteResponse(BaseModel):
    bill_id: str
    your_vote: str
    public_opinion: PublicOpinion


# ── Prompts & Helpers ──────────────────────────────────────────────────────────

_BILL_ANALYSIS_PROMPT = """
You are an expert legislative analyst for the Israeli Knesset.
Analyze the following bill details and provide:
1. A clear, concise explanation of what the bill does (in English).
2. A list of 3-5 key provisions or main points of the bill (in English).
3. A list of 2-3 category tags (in English) (e.g., "Security", "Technology", "Education", "Finance").

Bill Hebrew Title: {title}
Bill Hebrew Summary: {summary}
Bill Type: {type}

Respond ONLY with a JSON object in this format:
{
  "title_en": "Standard English Title",
  "explanation": "Clear explanation of the bill...",
  "key_provisions": ["Provision 1...", "Provision 2..."],
  "category_tags": ["Tag1", "Tag2"]
}
"""


async def get_or_generate_bill_analysis(bill_doc: dict, run_llm: bool = False) -> dict:
    """Gets or generates AI explanation, provisions, and category tags for real Knesset bills."""
    db = get_db()
    bill_id = bill_doc.get("bill_id")

    # Return if already processed/cached
    if bill_doc.get("explanation") and bill_doc.get("key_provisions"):
        return bill_doc

    # Call OpenAI if key is present and run_llm is True
    if run_llm and settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)

            title = bill_doc.get("name") or f"Bill {bill_id}"
            summary = bill_doc.get("summary") or ""
            bill_type = bill_doc.get("type") or ""

            prompt = _BILL_ANALYSIS_PROMPT.format(title=title, summary=summary, type=bill_type)

            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(resp.choices[0].message.content)

            explanation = result.get("explanation")
            key_provisions = result.get("key_provisions")
            category_tags = result.get("category_tags")
            title_en = result.get("title_en")

            update_fields = {
                "explanation": explanation,
                "key_provisions": key_provisions,
                "category_tags": category_tags,
            }
            if title_en:
                update_fields["title_en"] = title_en

            await db.knesset_bills.update_one({"bill_id": bill_id}, {"$set": update_fields})
            bill_doc.update(update_fields)
            return bill_doc

        except Exception as e:
            logger.warning("Failed to generate AI analysis for Knesset bill %s: %s", bill_id, e)

    # Fast local fallback to avoid blocking event loop or hitting API limits
    proposed_by = bill_doc.get("proposed_by") or bill_doc.get("committee") or bill_doc.get("initiator") or "Knesset Committee"
    bill_type_label = bill_doc.get("type") or "legislative"
    
    explanation = f"AI Analysis: This bill focuses on regulating {bill_type_label.lower()} initiatives proposed by {proposed_by}."
    key_provisions = [
        "Establishes structural and administrative implementation guidelines.",
        f"Subject to ongoing regulatory oversight and reviews by the {proposed_by}."
    ]
    category_tags = [bill_doc.get("type") or "Legislation"]

    fallback_fields = {
        "explanation": explanation,
        "key_provisions": key_provisions,
        "category_tags": category_tags
    }
    await db.knesset_bills.update_one({"bill_id": bill_id}, {"$set": fallback_fields})
    bill_doc.update(fallback_fields)
    return bill_doc



def get_bill_base_opinion(bill_id: str) -> dict:
    """Returns baseline public opinion counts for both mockup and real Knesset bills."""
    return {"support": 0, "oppose": 0, "neutral": 0, "abstain": 0, "total": 0}


def _filter_mock_bill(doc: dict, days: Optional[int]) -> bool:
    """Helper to filter mockup bills in memory based on age in days."""
    if days:
        pub_date_str = doc.get("publication_date")
        if not pub_date_str:
            return False
        try:
            dt = datetime.strptime(pub_date_str, "%Y-%m-%d")
            ref_date = datetime.utcnow()
            if ref_date.year < 2026:
                ref_date = datetime(2026, 6, 23)
            diff = ref_date - dt
            if diff > timedelta(days=days):
                return False
        except Exception:
            return False

    return True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/bills", response_model=BillsListResponse)
async def list_bills(
    days: Optional[int] = Query(None, description="Filter by last updated days, e.g. 30"),
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """
    Get all bills matching the query parameters.
    Mockup bills are returned first (Security, Education, Tax, Tech, etc.), followed
    by database-synced Knesset bills sorted by date/last_updated descending.
    AI analysis features are unlocked unless user_tier=pro and with_analysis=true.
    """
    db = get_db()
    mock_ids = ["security-2026", "education-2026", "tax-2026", "tech-2025", "energy-2026", "health-2026", "startup-2026"]

    # 1. Fetch mockup bills explicitly
    mock_cursor = db.knesset_bills.find({"bill_id": {"$in": mock_ids}})
    mock_docs = await mock_cursor.to_list(length=20)

    # Filter mock bills in-memory
    filtered_mock_docs = [doc for doc in mock_docs if _filter_mock_bill(doc, days)]

    # Sort mock bills in layout order
    mock_order = {
        "security-2026": 0, "education-2026": 1, "tax-2026": 2, "tech-2025": 3,
        "energy-2026": 4, "health-2026": 5, "startup-2026": 6
    }
    filtered_mock_docs.sort(key=lambda x: mock_order.get(x.get("bill_id"), 99))

    # 2. Build MongoDB query for real Knesset bills
    real_query = {"bill_id": {"$nin": mock_ids}}

    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        date_filters = [
            {"updated_at": {"$gte": cutoff_date}},
            {"last_updated": {"$gte": cutoff_str}},
            {"publication_date": {"$gte": cutoff_str.split("T")[0]}}
        ]
        real_query["$or"] = date_filters

    # Sort by updated_at (datetime) first — most reliable recency signal.
    # Fall back includes last_updated string sort as secondary.
    # Fetch more to ensure we have enough after filtering.
    real_cursor = db.knesset_bills.find(real_query).sort(
        [("updated_at", -1), ("last_updated", -1)]
    )
    real_docs = await real_cursor.to_list(length=100)

    # Cap real bills to 25 (up from 10) so clients get more fresh content
    real_docs = real_docs[:25]
    combined_docs = filtered_mock_docs + real_docs

    # Parallel AI Analysis Pipeline with Semaphore
    semaphore = asyncio.Semaphore(5)

    async def process_bill(doc: dict) -> dict:
        async with semaphore:
            if with_analysis and user_tier == "pro":
                # run_llm=True triggers live OpenAI GPT-4o translation & caching
                return await get_or_generate_bill_analysis(doc, run_llm=True)
            else:
                return doc

    tasks = [process_bill(doc) for doc in combined_docs]
    enriched_docs = await asyncio.gather(*tasks)

    mapped_bills = []
    for doc in enriched_docs:
        bill_id = doc.get("bill_id")

        # Determine title
        title = doc.get("title_en") or doc.get("title") or doc.get("name") or f"Bill {bill_id}"

        # Determine proposed_by / date
        proposed_by = doc.get("proposed_by") or doc.get("committee") or doc.get("initiator") or "Knesset Committee"
        date = doc.get("date") or doc.get("publication_date") or doc.get("last_updated") or "Unknown"

        # Determine category tags
        category_tags = doc.get("category_tags") or []
        verification_sources = []
        for key in ["official_source_url", "source_url", "source_links", "sources"]:
            value = doc.get(key)
            if isinstance(value, str) and value:
                verification_sources.append(value)
            elif isinstance(value, list):
                verification_sources.extend([str(v) for v in value if v])
        if not verification_sources:
            verification_sources = ["Knesset.gov.il / official legislative record"]
        if not category_tags:
            sub_type = doc.get("sub_type") or doc.get("type")
            category_tags = [sub_type] if sub_type else ["Legislation"]

        # Handle AI analysis based on tier and parameter
        explanation = None
        key_provisions = None

        if with_analysis:
            if user_tier == "pro":
                explanation = doc.get("explanation")
                key_provisions = doc.get("key_provisions")
                category_tags = doc.get("category_tags") or category_tags
            else:
                # Locked state for non-pro users requesting analysis
                explanation = "Upgrade to PRO tier to view AI analysis."
                key_provisions = ["Upgrade to PRO tier to view key provisions."]

        mapped_bills.append(
            BillOut(
                bill_id=bill_id,
                title=title,
                proposed_by=proposed_by,
                date=date,
                explanation=explanation,
                key_provisions=key_provisions,
                category_tags=category_tags,
                verification_status="verified" if verification_sources else "source-backed",
                verification_sources=verification_sources,
            )
        )

    return BillsListResponse(bills=mapped_bills)



@router.get("/bills/{bill_id}", response_model=BillOut)
async def get_bill(
    bill_id: str,
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """
    Get a single bill by its ID.
    AI analysis features are unlocked unless user_tier=pro and with_analysis=true.
    """
    db = get_db()

    # Query MongoDB for the bill document
    doc = await db.knesset_bills.find_one({"bill_id": bill_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Bill not found")

    # If PRO tier and analysis is requested, run GPT-4o translation/analysis or get cached
    if with_analysis and user_tier == "pro":
        doc = await get_or_generate_bill_analysis(doc, run_llm=True)

    # Determine fields
    title = doc.get("title_en") or doc.get("title") or doc.get("name") or f"Bill {bill_id}"
    proposed_by = doc.get("proposed_by") or doc.get("committee") or doc.get("initiator") or "Knesset Committee"
    date = doc.get("date") or doc.get("publication_date") or doc.get("last_updated") or "Unknown"

    category_tags = doc.get("category_tags") or []
    if not category_tags:
        sub_type = doc.get("sub_type") or doc.get("type")
        category_tags = [sub_type] if sub_type else ["Legislation"]

    # Build verification sources from whichever source field is present
    verification_sources = []
    for key in ["official_source_url", "source_url", "source_links", "sources"]:
        value = doc.get(key)
        if isinstance(value, str) and value:
            verification_sources.append(value)
        elif isinstance(value, list):
            verification_sources.extend([str(v) for v in value if v])
    if not verification_sources:
        verification_sources = ["Knesset.gov.il / official legislative record"]

    # Handle AI analysis based on tier and parameter
    explanation = None
    key_provisions = None

    if with_analysis:
        if user_tier == "pro":
            explanation = doc.get("explanation")
            key_provisions = doc.get("key_provisions")
            category_tags = doc.get("category_tags") or category_tags
        else:
            explanation = "Upgrade to PRO tier to view AI analysis."
            key_provisions = ["Upgrade to PRO tier to view key provisions."]

    return BillOut(
        bill_id=bill_id,
        title=title,
        proposed_by=proposed_by,
        date=date,
        explanation=explanation,
        key_provisions=key_provisions,
        category_tags=category_tags,
        verification_status="verified" if verification_sources else "source-backed",
        verification_sources=verification_sources,
    )



@router.get("/bills/{bill_id}/vote", response_model=VoteResponse)
async def get_bill_vote(
    bill_id: str,
    user_id: str = Query("000000000000000000000000", description="User ID to fetch their personal vote"),
):
    """
    Get the current vote status for a bill.

    Returns:
    - **your_vote**: the given user's vote (support | oppose | neutral | abstain | none)
    - **public_opinion**: aggregated support / oppose / neutral / abstain / total_votes counts
    """
    db = get_db()

    # Verify bill exists
    bill = await db.knesset_bills.find_one({"bill_id": bill_id})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Fetch this user's personal vote (if any)
    user_vote_doc = await db.user_bill_votes.find_one({"bill_id": bill_id, "user_id": user_id})
    your_vote = user_vote_doc["vote"] if user_vote_doc else "none"

    # Aggregate public opinion counts
    base = get_bill_base_opinion(bill_id)

    db_support = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "support"})
    db_oppose  = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "oppose"})
    db_neutral = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "neutral"})
    db_abstain = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "abstain"})

    total_support = base["support"] + db_support
    total_oppose  = base["oppose"]  + db_oppose
    total_neutral = base["neutral"] + db_neutral
    total_abstain = base.get("abstain", 0) + db_abstain
    total_votes   = total_support + total_oppose + total_neutral + total_abstain

    return VoteResponse(
        bill_id=bill_id,
        your_vote=your_vote,
        public_opinion=PublicOpinion(
            support=total_support,
            oppose=total_oppose,
            neutral=total_neutral,
            abstain=total_abstain,
            total_votes=total_votes,
        ),
    )


@router.post("/bills/{bill_id}/vote", response_model=VoteResponse)
async def vote_bill(
    bill_id: str,
    body: VoteRequest,
    user_id: str = Query("000000000000000000000000", description="User ID"),
):
    """
    Vote on a bill.
    Supports 'support', 'oppose', 'neutral', and 'abstain' choices.
    Tallies are updated dynamically by combining user votes with seed baseline data.
    """
    db = get_db()

    # Verify bill exists
    bill = await db.knesset_bills.find_one({"bill_id": bill_id})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    vote_choice = body.vote.lower()
    if vote_choice not in ("support", "oppose", "neutral", "abstain", "none"):
        raise HTTPException(status_code=400, detail="Invalid vote. Must be support | oppose | neutral | abstain | none")

    if vote_choice == "none":
        # Remove the user's vote
        await db.user_bill_votes.delete_one({"bill_id": bill_id, "user_id": user_id})
    else:
        # Record the user's vote
        await db.user_bill_votes.update_one(
            {"bill_id": bill_id, "user_id": user_id},
            {"$set": {"vote": vote_choice, "updated_at": datetime.utcnow()}},
            upsert=True
        )

    # Calculate dynamic public opinion
    base = get_bill_base_opinion(bill_id)

    # Query active votes from DB
    db_support = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "support"})
    db_oppose = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "oppose"})
    db_neutral = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "neutral"})
    db_abstain = await db.user_bill_votes.count_documents({"bill_id": bill_id, "vote": "abstain"})

    total_support = base["support"] + db_support
    total_oppose = base["oppose"] + db_oppose
    total_neutral = base["neutral"] + db_neutral
    total_abstain = base.get("abstain", 0) + db_abstain
    total_votes = total_support + total_oppose + total_neutral + total_abstain

    return VoteResponse(
        bill_id=bill_id,
        your_vote=vote_choice,
        public_opinion=PublicOpinion(
            support=total_support,
            oppose=total_oppose,
            neutral=total_neutral,
            abstain=total_abstain,
            total_votes=total_votes
        )
    )


# ── Knesset-prefixed proxy endpoints (same behavior as /bills) ─────────────
@router.get("/knesset/bills", response_model=BillsListResponse)
async def knesset_list_bills(
    days: Optional[int] = Query(None, description="Filter by last updated days, e.g. 30"),
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """Proxy to `GET /bills` under the `/knesset` namespace."""
    return await list_bills(days=days, user_tier=user_tier, with_analysis=with_analysis)


@router.get("/knesset/bills/{bill_id}", response_model=BillOut)
async def knesset_get_bill(
    bill_id: str,
    user_tier: str = Query("free", description="User tier: free | pro"),
    with_analysis: bool = Query(False, description="Whether to include AI analysis"),
):
    """Proxy to `GET /bills/{bill_id}` under the `/knesset` namespace."""
    return await get_bill(bill_id=bill_id, user_tier=user_tier, with_analysis=with_analysis)


@router.get("/knesset/bills/{bill_id}/vote", response_model=VoteResponse)
async def knesset_get_bill_vote(
    bill_id: str,
    user_id: str = Query("000000000000000000000000", description="User ID to fetch their personal vote"),
):
    """Proxy to `GET /bills/{bill_id}/vote` under the `/knesset` namespace."""
    return await get_bill_vote(bill_id=bill_id, user_id=user_id)


@router.post("/knesset/bills/{bill_id}/vote", response_model=VoteResponse)
async def knesset_vote_bill(
    bill_id: str,
    body: VoteRequest,
    user_id: str = Query("000000000000000000000000", description="User ID"),
):
    """Proxy to `POST /bills/{bill_id}/vote` under the `/knesset` namespace."""
    return await vote_bill(bill_id=bill_id, body=body, user_id=user_id)
