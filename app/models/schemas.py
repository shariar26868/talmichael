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
    link: str
    description: str
    pub_date: str
    source: Optional[str] = None
    source_url: Optional[str] = None
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
