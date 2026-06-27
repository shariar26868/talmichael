# app/routes/election_voting.py
"""
Election Voting & Poll Routes.
Maps to the Election Section (Screen 6).
Covers: community party vote, community candidate vote, poll results,
election timeline, election news feed, and candidate list.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.election_voting_service import (
    vote_for_party,
    vote_for_candidate,
    get_party_poll,
    get_candidate_poll,
    get_election_timeline,
    get_election_news,
    get_election_candidates_list,
    get_election_participants,
)

router = APIRouter(prefix="/elections/2026", tags=["Election 2026"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PartyVoteRequest(BaseModel):
    party_name: str
    user_id: str  # anonymous UUID or authenticated user ID


class CandidateVoteRequest(BaseModel):
    candidate_name: str
    party_name: Optional[str] = None
    user_id: str


# ── Community Voting ──────────────────────────────────────────────────────────

@router.post(
    "/vote/party",
    summary="Vote for your favorite party (2026 election)",
    description=(
        "Submit a community vote for your preferred political party in the 2026 Israeli election. "
        "Each user can vote once (last vote overwrites previous). "
        "Results are shown in the Election Section community poll. "
        "ALL parties from the 2026 election are eligible."
    ),
)
async def vote_party(body: PartyVoteRequest):
    """Submit a community vote for a political party."""
    result = await vote_for_party(
        party_name=body.party_name,
        user_id=body.user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/vote/candidate",
    summary="Vote for your favorite candidate (2026 election)",
    description=(
        "Submit a community vote for your preferred candidate/politician in the 2026 Israeli election. "
        "Each user can vote once (last vote overwrites previous). "
        "ALL Knesset members and announced candidates are eligible."
    ),
)
async def vote_candidate(body: CandidateVoteRequest):
    """Submit a community vote for a candidate."""
    result = await vote_for_candidate(
        candidate_name=body.candidate_name,
        party_name=body.party_name or "",
        user_id=body.user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Poll Results ──────────────────────────────────────────────────────────────

@router.get(
    "/poll/parties",
    summary="Community party poll results (2026 election)",
    description=(
        "Returns real-time community poll results showing which party users prefer. "
        "Shows ALL parties, vote counts, and percentages. "
        "Note: This is a community preference poll — not an official election poll."
    ),
)
async def party_poll():
    """Get community poll results for parties in the 2026 election."""
    return await get_party_poll()


@router.get(
    "/poll/candidates",
    summary="Community candidate poll results (2026 election)",
    description=(
        "Returns real-time community poll results showing which candidates users prefer. "
        "Shows ALL candidates, vote counts, and percentages. "
        "Note: This is a community preference poll — not an official election poll."
    ),
)
async def candidate_poll():
    """Get community poll results for candidates in the 2026 election."""
    return await get_candidate_poll()


# ── Election Timeline ─────────────────────────────────────────────────────────

@router.get(
    "/timeline",
    summary="2026 election key milestones timeline",
    description=(
        "Returns the timeline of key milestones for the 2026 Israeli election: "
        "Party Registration Deadline, Campaign Launch, Election Day, and more. "
        "Data sourced from bechirot.gov.il (Central Elections Committee) — not AI-generated."
    ),
)
async def election_timeline():
    """Get the 2026 election timeline with key milestones."""
    return await get_election_timeline()


# ── Election News ─────────────────────────────────────────────────────────────

@router.get(
    "/news",
    summary="News articles about the 2026 election",
    description=(
        "Returns news articles specifically related to the upcoming 2026 Israeli election. "
        "Articles are filtered by election-relevant keywords in English and Hebrew. "
        "Optionally filter by news category."
    ),
)
async def election_news(
    category: Optional[str] = Query(
        None,
        description="Filter by category: 'politics' | 'security' | 'economy'",
    ),
    limit: int = Query(20, ge=1, le=50, description="Number of articles to return"),
):
    """Get news articles about the 2026 election."""
    return await get_election_news(category=category, limit=limit)


# ── Candidates List ───────────────────────────────────────────────────────────

@router.get(
    "/candidates",
    summary="All 2026 election candidates list",
    description=(
        "Returns a list of all candidates (current MPs + announced candidates) "
        "eligible to run in the 2026 election. "
        "Includes name, party, photo, and bloc affiliation. "
        "Use this to populate the candidate voting poll dropdown."
    ),
)
async def election_candidates():
    """Get all candidates eligible to run in the 2026 election."""
    return await get_election_candidates_list()


@router.get(
    "/participants",
    summary="All parties and candidates for the 2026 election",
    description=(
        "Returns a combined list of all parties and active candidates for the 2026 election. "
        "Each item includes a unique id and a type field: 'party' or 'candidate'."
    ),
)
async def election_participants():
    """Get a unified list of parties and candidates for the 2026 election."""
    return await get_election_participants()
