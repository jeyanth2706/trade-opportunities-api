# Trade Opportunities API

A FastAPI service that fetches **live market data** via real-time web search and generates AI-powered trade opportunity analysis reports for Indian market sectors.

---

## Features

- **Real-time data collection** — DuckDuckGo live web search (no static/hardcoded data)
- **AI-powered reports** — Google Gemini for deep analysis; structured fallback if Gemini is unavailable
- **Session management** — auto-created guest sessions, 24h expiry, in-memory storage
- **Rate limiting** — sliding-window per session (configurable via env vars)
- **Input validation** — sector whitelist, case-insensitive, Pydantic models
- **Security** — session tokens, rate limiting with `Retry-After` headers
- **Auto docs** — Swagger UI at `/docs`, ReDoc at `/redoc`
- **Health check** — `/api/v1/health`
- **12 supported sectors** — easily extensible

---

## Supported Sectors

| Sector | Key Focus |
|--------|-----------|
| `pharmaceuticals` | Generics, exports, biologics |
| `technology` | IT services, AI, cloud |
| `agriculture` | Agritech, exports, commodities |
| `banking` | NPA trends, credit growth, RBI policy |
| `automobile` | EVs, exports, new models |
| `it` | Software services, generative AI |
| `energy` | Renewables, solar, green hydrogen |
| `retail` | E-commerce, omnichannel, consumer spending |
| `infrastructure` | Capex, roads, ports |
| `fmcg` | Volume growth, rural demand |
| `telecom` | 5G rollout, ARPU, spectrum |
| `metals` | Steel, aluminium, mining |

---

## Quick Start

### 1. Clone and set up

```bash
git clone <repo-url>
cd trade-api
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 3. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Analyze the pharmaceuticals sector
curl http://localhost:8000/api/v1/analyze/pharmaceuticals

# List supported sectors
curl http://localhost:8000/api/v1/sectors

# Health check
curl http://localhost:8000/api/v1/health

# Use a session token (from a previous response's session_id)
curl -H "X-Session-Token: <your-token>" http://localhost:8000/api/v1/analyze/technology
```

---

## API Reference

### `GET /api/v1/analyze/{sector}`

Fetches live market data and returns a markdown analysis report.

**Path parameter:** `sector` — one of the supported sector names (case-insensitive)

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-Token` | No | Session token from a previous response. Omit to auto-create a new session. |

**Response:**
```json
{
  "sector": "pharmaceuticals",
  "report": "# Trade Opportunity Analysis: Pharmaceuticals Sector\n\n...",
  "generated_at": "2025-04-08T10:30:00",
  "session_id": "abc123...",
  "cache_hit": false,
  "news_count": 12,
  "companies_found": 7
}
```

**Error codes:**
| Code | Meaning |
|------|---------|
| 400 | Unsupported sector |
| 401 | Invalid/expired session token |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

### `GET /api/v1/sectors`

Returns a list of all supported sectors.

### `GET /api/v1/health`

Returns service health, Gemini availability, and active session count.

---

## Rate Limiting

- **Default:** 10 requests per 60 seconds per session
- **Algorithm:** Sliding window (in-memory)
- **Response on limit:** HTTP 429 with `Retry-After` header
- **Configurable** via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD` env vars

---

## Authentication & Sessions

- Sessions are **auto-created** for unauthenticated requests — no signup required
- The session token is returned in every response as `session_id`
- Pass it back as `X-Session-Token` header to maintain your session and quota
- Sessions expire after 24 hours (configurable via `SESSION_TIMEOUT_HOURS`)

---

## Architecture

```
main.py                  ← FastAPI app, lifecycle, middleware
app/
  config.py              ← Environment config + validation
  models.py              ← Pydantic request/response models
  auth.py                ← Session management + auth dependency
  rate_limiter.py        ← Sliding-window rate limiter dependency
  data_collector.py      ← Live DuckDuckGo web search (no static data)
  ai_analyzer.py         ← Gemini AI analysis + structured fallback
  routes.py              ← API endpoints with proper Depends() wiring
tests/
  test_api.py            ← Full test suite (unit + integration)
```

### Data flow per request

```
Request → authenticate_request (Depends) → rate_limit_dependency (Depends)
        → MarketDataCollector.search_market_data()   ← DuckDuckGo live search
        → AIAnalyzer.generate_analysis_report()      ← Gemini or fallback
        → AnalysisResponse (JSON)
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(none)* | Google Gemini API key (required for AI reports) |
| `SECRET_KEY` | `changeme-...` | Application secret (change in production) |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per window |
| `RATE_LIMIT_PERIOD` | `60` | Window size in seconds |
| `SESSION_TIMEOUT_HOURS` | `24` | Session expiry |
| `SEARCH_MAX_RESULTS` | `10` | DuckDuckGo results per query |
| `CACHE_TTL_SECONDS` | `300` | Sector data cache duration (5 min) |

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Notes

- The fallback report generator uses **only live-fetched data** — it never outputs static placeholder text
- Gemini is optional; the service is fully functional without it
- All storage is in-memory; the service is stateless across restarts (by design)
- Caching reduces redundant searches for the same sector within 5 minutes
