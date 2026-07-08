# app/routes/election_voting.py
"""
Election Voting & Poll Routes.
Maps to the Election Section (Screen 6).
Covers: community party vote, community candidate vote, poll results,
election timeline, election news feed, candidate list,
and full party roster for the 2026 Israeli election.
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
from app.services.election_service import (
    get_parties_for_2026,
    get_election_overview,
    get_election_issues,
    get_election_blocs,
)

router = APIRouter(prefix="/elections/2026", tags=["Election 2026"])


# ── Election Overview & Context ───────────────────────────────────────────────

@router.get(
    "/overview",
    summary="2026 Israeli election overview",
    description=(
        "Returns the full context for the 2026 (26th Knesset) Israeli election: "
        "scheduled date, total seats (120), electoral threshold (3.25%), bloc projections, "
        "and key background context. "
        "Data sourced from Wikipedia, bechirot.gov.il, and Israel Policy Forum — not AI-generated."
    ),
)
async def election_overview():
    """Get the full 2026 election overview with date, blocs, and context."""
    return get_election_overview()


# ── All 2026 Election Parties ─────────────────────────────────────────────────

@router.get(
    "/parties",
    summary="All parties running in the 2026 Israeli election",
    description=(
        "Returns the complete roster of ALL political parties expected to contest the "
        "26th Knesset (2026) election. "
        "Includes: party name (English + Hebrew), leader name, political wing (left/center/right/far-right), "
        "bloc (coalition/opposition/arab_parties), key campaign platform points, polling seat range, "
        "official website, and Wikipedia link. "
        "Optionally filter by bloc: 'coalition', 'opposition', or 'arab_parties'. "
        "Data sourced from Wikipedia, Times of Israel, and official party websites — not AI-generated. "
        "Use this endpoint to populate the 'Vote for Your Party' and 'Vote for Your Candidate' UI sections."
    ),
)
async def election_parties(
    bloc: Optional[str] = Query(
        None,
        description="Filter by bloc: 'coalition' | 'opposition' | 'arab_parties'",
    ),
):
    """Get all 2026 election parties, optionally filtered by bloc."""
    parties = get_parties_for_2026(bloc=bloc)
    return {
        "election_year": 2026,
        "total": len(parties),
        "bloc_filter": bloc,
        "parties": parties,
        "blocs_available": ["coalition", "opposition", "arab_parties"],
        "note": (
            "All parties are expected to contest the 2026 Israeli legislative election. "
            "Poll seat ranges are approximate as of June 2026 and vary by pollster."
        ),
        "data_freshness": "2026-06-15",
        "data_source": "Wikipedia, Times of Israel, official party websites — not AI-generated",
    }


@router.get(
    "/issues",
    summary="Key campaign issues for the 2026 election",
    description=(
        "Returns the main political issues shaping the 2026 Israeli election campaign. "
        "Each issue includes which party blocs are for or against it."
    ),
)
async def election_issues_route():
    """Get key campaign issues for the 2026 election."""
    return {
        "election_year": 2026,
        "issues": get_election_issues(),
        "data_freshness": "2026-06-15",
    }


@router.get(
    "/blocs",
    summary="2026 election bloc projections",
    description=(
        "Returns current polling bloc projections: coalition, Zionist opposition, and Arab parties. "
        "Includes approximate total seats per bloc and notes on majority formation."
    ),
)
async def election_blocs_route():
    """Get the 2026 election bloc projections."""
    return get_election_blocs()


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


@router.get(
    "/articles",
    summary="Election articles (alias)",
    description="Alias for the election news endpoint used by the election card UI.",
)
async def election_articles(
    category: Optional[str] = Query(
        None,
        description="Filter by category: 'politics' | 'security' | 'economy'",
    ),
    limit: int = Query(20, ge=1, le=50, description="Number of articles to return"),
):
    """Alias to return election news articles in a UI-friendly shape."""
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
