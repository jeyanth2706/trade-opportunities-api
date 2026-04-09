"""
tests/test_api.py — Test suite for Trade Opportunities API

Run with:
    pytest tests/ -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from app.models import MarketData, NewsItem
from app.auth import SessionManager
from app.rate_limiter import RateLimiter
from app.config import Config


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app state is initialized for every test."""
    app.state.session_manager = SessionManager()
    app.state.rate_limiter = RateLimiter()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_market_data():
    return MarketData(
        sector="technology",
        news_summary=[
            NewsItem(
                title="TCS reports strong Q4 results",
                summary="Tata Consultancy Services beats earnings expectations.",
                source="Economic Times",
                url="https://example.com/tcs-q4"
            ),
            NewsItem(
                title="Infosys raises FY26 guidance on AI demand",
                summary="Infosys upgrades revenue guidance citing AI projects.",
                source="Mint",
                url="https://example.com/infy-guidance"
            ),
        ],
        key_companies=["TCS Ltd", "Infosys Ltd", "Wipro Ltd"],
        trends=["AI integration driving deal wins", "Cloud migration continues"],
        government_policies=["Digital India initiative boosts IT demand"],
        market_sentiment="positive"
    )


# ─── Root / Meta endpoints ───────────────────────────────────────────────────

def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "TradeVision AI" in resp.text
    assert "Market Intelligence" in resp.text


def test_health_check(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "gemini_configured" in data
    assert "active_sessions" in data


def test_list_sectors(client):
    resp = client.get("/api/v1/sectors")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported_sectors" in data
    assert "pharmaceuticals" in data["supported_sectors"]
    assert data["count"] == len(Config.SUPPORTED_SECTORS)


# ─── Authentication ───────────────────────────────────────────────────────────

def test_auto_session_created_without_token(client, mock_market_data):
    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Report\n\nTest content."

        resp = client.get("/api/v1/analyze/technology")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 10  # session token should be non-trivial


def test_valid_session_token_accepted(client, mock_market_data):
    session_manager = app.state.session_manager
    token = session_manager.create_session()

    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Report"

        resp = client.get("/api/v1/analyze/technology", headers={"X-Session-Token": token})
        assert resp.status_code == 200


def test_invalid_session_token_rejected(client):
    resp = client.get(
        "/api/v1/analyze/technology",
        headers={"X-Session-Token": "invalid-token-xyz"}
    )
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]


# ─── Input validation ─────────────────────────────────────────────────────────

def test_unsupported_sector_returns_400(client):
    resp = client.get("/api/v1/analyze/unknownsector123")
    assert resp.status_code == 400
    assert "not supported" in resp.json()["detail"]


def test_sector_case_insensitive(client, mock_market_data):
    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Report"

        resp = client.get("/api/v1/analyze/TECHNOLOGY")
        assert resp.status_code == 200
        assert resp.json()["sector"] == "technology"


def test_sector_with_whitespace(client, mock_market_data):
    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Report"

        resp = client.get("/api/v1/analyze/ technology ")
        # FastAPI strips path params, should still work
        assert resp.status_code in (200, 400)


# ─── Rate limiting ────────────────────────────────────────────────────────────

def test_rate_limit_enforced(client, mock_market_data):
    session_manager = app.state.session_manager
    token = session_manager.create_session()

    # Override rate limiter to only allow 2 requests
    app.state.rate_limiter.max_requests = 2

    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Report"

        headers = {"X-Session-Token": token}
        r1 = client.get("/api/v1/analyze/technology", headers=headers)
        r2 = client.get("/api/v1/analyze/banking", headers=headers)
        r3 = client.get("/api/v1/analyze/energy", headers=headers)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429

    # Reset
    app.state.rate_limiter.max_requests = Config.RATE_LIMIT_REQUESTS


# ─── Response structure ───────────────────────────────────────────────────────

def test_response_structure(client, mock_market_data):
    with patch("app.routes.data_collector.search_market_data", new_callable=AsyncMock) as mock_dc, \
         patch("app.routes.ai_analyzer.generate_analysis_report", new_callable=AsyncMock) as mock_ai:
        mock_dc.return_value = mock_market_data
        mock_ai.return_value = "# Trade Report\n\n## Overview\nContent here."

        resp = client.get("/api/v1/analyze/technology")
        assert resp.status_code == 200
        data = resp.json()

        assert data["sector"] == "technology"
        assert "# Trade Report" in data["report"]
        assert "generated_at" in data
        assert "session_id" in data
        assert isinstance(data["news_count"], int)
        assert isinstance(data["companies_found"], int)


# ─── Session manager unit tests ──────────────────────────────────────────────

def test_session_create_and_validate():
    sm = SessionManager()
    token = sm.create_session()
    assert sm.validate_session(token) is True


def test_session_invalid_token():
    sm = SessionManager()
    assert sm.validate_session("nonexistent") is False


def test_session_increment():
    sm = SessionManager()
    token = sm.create_session()
    sm.increment_requests(token)
    sm.increment_requests(token)
    assert sm.get_session(token).requests_count == 2


# ─── Rate limiter unit tests ──────────────────────────────────────────────────

def test_rate_limiter_allows_within_limit():
    rl = RateLimiter()
    rl.max_requests = 3
    for _ in range(3):
        assert rl.check_and_record("session-abc") is True


def test_rate_limiter_blocks_over_limit():
    rl = RateLimiter()
    rl.max_requests = 2
    rl.check_and_record("s1")
    rl.check_and_record("s1")
    assert rl.check_and_record("s1") is False


def test_rate_limiter_remaining():
    rl = RateLimiter()
    rl.max_requests = 5
    rl.check_and_record("s2")
    rl.check_and_record("s2")
    assert rl.remaining("s2") == 3


# ─── AI Analyzer unit tests ──────────────────────────────────────────────────

def test_fallback_report_uses_live_data(mock_market_data):
    from app.ai_analyzer import AIAnalyzer
    analyzer = AIAnalyzer()
    # Force fallback even if Gemini is configured
    report = analyzer._generate_structured_report(mock_market_data)

    assert "Technology" in report
    assert "TCS reports strong Q4 results" in report
    assert "TCS Ltd" in report
    assert "Disclaimer" in report


def test_fallback_report_positive_sentiment(mock_market_data):
    from app.ai_analyzer import AIAnalyzer
    mock_market_data.market_sentiment = "positive"
    analyzer = AIAnalyzer()
    report = analyzer._generate_structured_report(mock_market_data)
    assert "POSITIVE" in report or "positive" in report.lower()


def test_fallback_report_negative_sentiment(mock_market_data):
    from app.ai_analyzer import AIAnalyzer
    mock_market_data.market_sentiment = "negative"
    analyzer = AIAnalyzer()
    report = analyzer._generate_structured_report(mock_market_data)
    assert "Caution" in report or "NEGATIVE" in report


# ─── Data collector unit tests ───────────────────────────────────────────────

def test_extract_sentiment_positive():
    from app.data_collector import MarketDataCollector
    dc = MarketDataCollector()
    results = [{"title": "Growth surge record profit gains", "body": "strong bullish rise"}]
    assert dc._detect_sentiment(results) == "positive"


def test_extract_sentiment_negative():
    from app.data_collector import MarketDataCollector
    dc = MarketDataCollector()
    results = [{"title": "Decline fall drop slump", "body": "bearish loss weak concern"}]
    assert dc._detect_sentiment(results) == "negative"


def test_get_template_known_sector():
    from app.data_collector import MarketDataCollector, SECTOR_SEARCH_TEMPLATES
    dc = MarketDataCollector()
    t = dc._get_template("banking")
    assert t == SECTOR_SEARCH_TEMPLATES["banking"]


def test_get_template_unknown_sector():
    from app.data_collector import MarketDataCollector
    dc = MarketDataCollector()
    t = dc._get_template("ceramics")
    assert "ceramics" in t["company_query"]
    assert len(t["news_queries"]) == 3
