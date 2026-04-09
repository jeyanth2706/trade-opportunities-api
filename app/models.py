from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional


class AnalysisResponse(BaseModel):
    sector: str
    report: str
    generated_at: datetime
    session_id: str
    cache_hit: bool = False
    news_count: int = 0
    companies_found: int = 0


class SessionData(BaseModel):
    session_id: str
    requests_count: int
    last_request_time: datetime
    created_at: datetime


class NewsItem(BaseModel):
    title: str
    summary: str
    source: str
    url: Optional[str] = None


class MarketData(BaseModel):
    sector: str
    news_summary: List[NewsItem] = []
    key_companies: List[str] = []
    trends: List[str] = []
    government_policies: List[str] = []
    market_sentiment: str = "neutral"


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int
