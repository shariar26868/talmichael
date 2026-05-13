#app/models.py

from pydantic import BaseModel
from typing import Optional, List


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


class NewsResponse(BaseModel):
    meta: FeedMeta
    total: int
    articles: List[NewsArticle]