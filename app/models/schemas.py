# app/models/schemas.py
"""Pydantic request/response schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ── News ──────────────────────────────────────────────────────────────────────

class FeedMeta(BaseModel):
    title: str
    description: str
    link: str
    last_build_date: str
    fetched_at: str


class NewsArticle(BaseModel):
    title: str
    source_type: Optional[str] = None
    link: str
    description: str
    pub_date: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    guid: Optional[str] = None
    # AI fields (populated when available)
    sentiment: Optional[str] = None
    bias: Optional[str] = None
    bias_score: Optional[float] = None
    bias_types: Optional[list[str]] = None
    bias_category: Optional[str] = None
    credibility_score: Optional[float] = None
    credibility_label: Optional[str] = None
    fact_check_score: Optional[float] = None
    summary_hebrew: Optional[str] = None
    topics: Optional[list[str]] = None
    claims: Optional[list[str]] = None
    factual_points: Optional[list[str]] = None
    claim_explanation: Optional[str] = None
    bias_explanation: Optional[str] = None


class NewsResponse(BaseModel):
    meta: FeedMeta
    total: int
    articles: list[NewsArticle]


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3–50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, _ and -")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tier: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    tier: str
    is_verified: bool
    model_config = {"from_attributes": True}


# ── AI Analysis ───────────────────────────────────────────────────────────────

class ArticleAnalysis(BaseModel):
    guid: str
    sentiment: str           # positive / neutral / negative
    bias: str                # left / center / right / unknown
    bias_score: float        # 0.0 – 1.0
    bias_types: list[str]    # e.g. loaded language, framing, source leaning
    bias_category: str       # descriptive bias category, e.g. Sensationalism, Loaded Language, Cherry-picking, Speculative Reporting, Partisan Framing, False Equivalence, Ad Hominem Attack, Context Omission, Emotional Appeal, Unsubstantiated Claims, Source Bias, Objective Reporting
    bias_score_explanation: str
    credibility_score: float # 0.0 – 1.0
    credibility_label: str   # verified / likely credible / needs review / unverified
    fact_check_score: float  # 0.0 – 1.0
    summary_hebrew: str
    topics: list[str]        # extracted key topics
    claims: list[str]
    factual_points: list[str]
    claim_explanation: str
    bias_explanation: str


class SourceBiasInfo(BaseModel):
    source_name: str
    bias: str
    credibility_score: float
    report_count: int


# ── Community ─────────────────────────────────────────────────────────────────

class CommunityArticleCreate(BaseModel):
    title: str
    content: str
    category: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Title must be at least 5 characters")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("Content must be at least 50 characters")
        return v.strip()


class CommunityArticleOut(BaseModel):
    id: int
    title: str
    content: str
    category: str
    status: str
    created_at: str
    model_config = {"from_attributes": True}


# ── Knesset ───────────────────────────────────────────────────────────────────

class BillVoteRequest(BaseModel):
    support: bool  # True = support, False = oppose


class BillSummaryOut(BaseModel):
    id: str
    bill_id: str
    name: str
    name_hebrew: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    sub_type: Optional[str] = None
    initiator: Optional[str] = None
    initiator_party: Optional[str] = None
    committee: Optional[str] = None
    summary: Optional[str] = None
    ai_summary: Optional[str] = None
    last_updated: Optional[str] = None
    source: Optional[str] = None
    # Visible connectivity info for UI: whether official Knesset API is reachable
    official_api_reachable: Optional[bool] = None
    official_api_notice: Optional[str] = None
    community_tally: Optional[dict] = None
    official_vote_summary: Optional[dict] = None
    model_config = {"from_attributes": True}


class BillVoteRecordOut(BaseModel):
    bill_id: str
    mp_id: Optional[str] = None
    knesset_person_id: Optional[str] = None
    mp_name: str
    party: Optional[str] = None
    vote: str
    vote_date: Optional[str] = None
    source: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Political ─────────────────────────────────────────────────────────────────

class PartyOut(BaseModel):
    id: int
    name: str
    name_hebrew: Optional[str] = None
    wing: Optional[str] = None
    seats: int
    leader: Optional[str] = None
    ideology: Optional[str] = None
    agenda: Optional[str] = None
    model_config = {"from_attributes": True}


class MPOut(BaseModel):
    id: int
    knesset_id: Optional[int] = None
    name: str
    name_hebrew: Optional[str] = None
    role: Optional[str] = None
    committee: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    consistency_score: Optional[float] = None
    party: Optional[PartyOut] = None
    model_config = {"from_attributes": True}


class MPQuoteCreate(BaseModel):
    quote: str
    context: Optional[str] = None
    source_url: Optional[str] = None
    topic: Optional[str] = None
    date: Optional[str] = None


class MPActionCreate(BaseModel):
    action: str
    action_type: Optional[str] = None
    topic: Optional[str] = None
    source_url: Optional[str] = None
    date: Optional[str] = None


class ContradictionOut(BaseModel):
    id: int
    mp_id: int
    explanation: str
    severity: str
    topic: Optional[str] = None
    detected_at: str
    model_config = {"from_attributes": True}


class CommitteeOut(BaseModel):
    id: int
    committee_id: int
    name: str
    name_hebrew: Optional[str] = None
    chair: Optional[str] = None
    description: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Verification & Framing Schemas ────────────────────────────────────────────

class VerifiedClaim(BaseModel):
    """A single claim extracted from an article with verification status."""
    claim_text: str
    verification_status: str  # verified / partially_verified / unverified / contradicted
    evidence_sources: list[str] = []  # Source names or URLs that support/contradict
    confidence: float = 0.5  # 0.0-1.0
    explanation: str = ""


class FramingAnalysis(BaseModel):
    """Detailed analysis of how a story is framed (not just what it says)."""
    headline_body_consistency: float = 1.0  # 0.0-1.0 (low = clickbait)
    attribution_count: int = 0  # how many named sources cited in the article
    perspective_balance: str = "unknown"  # "one-sided" / "balanced" / "multi-perspective"
    narrative_frame: str = "informational"  # conflict / human_interest / economic / morality / responsibility / informational
    voice_analysis: str = "mixed"  # "active" / "passive" / "mixed"
    omission_signals: list[str] = []  # e.g. "no opposing view cited", "statistics without context"


class CrossSourceMatch(BaseModel):
    """Result of comparing the same event across multiple sources."""
    event_cluster_id: str  # groups articles about the same event
    matching_articles: list[dict] = []  # [{source, title, bias, guid}]
    source_count: int = 0
    agreement_score: float = 0.5  # 0.0-1.0 (how consistent the reporting is)
    divergences: list[str] = []  # key differences across sources
    consensus_framing: Optional[str] = None  # what most sources agree on


class VerificationConfidence(BaseModel):
    """Composite verification score combining all available signals."""
    overall_score: float = 0.5  # 0.0-1.0
    components: dict = {}  # breakdown: source_credibility, cross_source_agreement, etc.
    label: str = "needs review"  # highly_verified / verified / partially_verified / needs_review / disputed
    explanation: str = ""


class AuditLogEntry(BaseModel):
    """Transparency record of how an article was analyzed."""
    article_id: str
    timestamp: str
    models_used: list[str] = []  # ["rule-based", "gpt-4o-mini", "gemini-2.0-flash"]
    user_vote_count: int = 0
    analysis_tier: str = "free"  # free / pro / platinum
    final_bias: str = "unknown"
    final_credibility: float = 0.5
    consensus_source: str = "ai"  # ai / user_consensus / mixed


# ── Voting & Credibility ──────────────────────────────────────────────────────

# Full bias spectrum — granular enough for Israeli media landscape
BIAS_SPECTRUM = (
    "far-left", "left", "center-left", "center",
    "center-right", "right", "far-right", "unclear",
)


class BiasVoteCreate(BaseModel):
    """User submits bias assessment for an article."""
    bias_assessment: str  # any value from BIAS_SPECTRUM
    confidence: float     # 0.0 - 1.0
    user_notes: Optional[str] = None

    @field_validator("bias_assessment")
    @classmethod
    def valid_bias(cls, v: str) -> str:
        if v not in BIAS_SPECTRUM:
            raise ValueError(
                f"bias_assessment must be one of: {', '.join(BIAS_SPECTRUM)}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def valid_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class CredibilityVoteCreate(BaseModel):
    """User votes on source credibility."""
    credibility_level: str  # "very_low" | "low" | "medium" | "high" | "very_high"
    evidence: Optional[str] = None


class FlagArticleCreate(BaseModel):
    """User flags article for misinformation or bias."""
    reason: str  # "misinformation" | "propaganda" | "biased" | "unreliable_source"
    details: str


class BiasVoteResponse(BaseModel):
    """Response after submitting bias vote."""
    status: str
    vote_id: str
    article_id: str
    recorded_at: str
    new_consensus: Optional[dict] = None


class CredibilityVoteResponse(BaseModel):
    """Response after submitting credibility vote."""
    status: str
    vote_id: str
    source_name: str
    recorded_at: str
    updated_credibility: Optional[dict] = None


class VoteStats(BaseModel):
    """Stats about votes on an article/source."""
    total_votes: int
    consensus: str  # The winning assessment
    consensus_percentage: float
    breakdown: dict  # {"left": 45, "center": 30, "right": 25}
    flagged: int  # Number of flags


class BiasConsensus(BaseModel):
    """Final bias assessment combining AI + user votes."""
    bias: str
    confidence: float
    based_on: str  # "ai" | "user_consensus" | "mixed"
    vote_count: int
    stats: Optional[VoteStats] = None


class CredibilityConsensus(BaseModel):
    """Final credibility assessment combining AI + user votes."""
    credibility_score: float  # 0.0 - 1.0
    credibility_label: str  # "verified" | "likely credible" | "needs review" | "unverified"
    based_on: str  # "ai" | "user_consensus" | "mixed"
    vote_count: int
    stats: Optional[VoteStats] = None
