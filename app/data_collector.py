import asyncio
import logging
import time
from typing import Dict, List, Optional
from duckduckgo_search import DDGS
from app.models import MarketData, NewsItem
from app.config import Config

logger = logging.getLogger(__name__)


# Sector-specific search templates to get precise, relevant results
SECTOR_SEARCH_TEMPLATES = {
    "pharmaceuticals": {
        "news_queries": [
            "India pharmaceutical sector stock market 2024 2025",
            "pharma companies India earnings results",
            "India drug exports FDA approval 2025",
        ],
        "company_query": "top pharmaceutical companies India NSE BSE listed",
        "policy_query": "India pharma government policy regulation 2025",
    },
    "technology": {
        "news_queries": [
            "India IT sector quarterly results 2025",
            "Indian technology companies growth AI 2025",
            "Infosys TCS Wipro earnings outlook",
        ],
        "company_query": "top IT technology companies India NSE listed",
        "policy_query": "Digital India IT policy government initiatives 2025",
    },
    "agriculture": {
        "news_queries": [
            "India agriculture sector stocks 2025",
            "agri commodities India market outlook",
            "India agritech investment 2025",
        ],
        "company_query": "top agriculture agritech companies India NSE BSE",
        "policy_query": "India agriculture government policy MSP 2025",
    },
    "banking": {
        "news_queries": [
            "India banking sector NPA credit growth 2025",
            "RBI policy banking sector outlook",
            "Indian banks quarterly results 2025",
        ],
        "company_query": "top banking financial companies India NSE listed",
        "policy_query": "RBI monetary policy banking regulation India 2025",
    },
    "automobile": {
        "news_queries": [
            "India automobile sector sales EV 2025",
            "Indian auto companies quarterly results",
            "EV electric vehicle India market 2025",
        ],
        "company_query": "top automobile companies India NSE BSE listed",
        "policy_query": "India EV policy FAME scheme automobile 2025",
    },
    "it": {
        "news_queries": [
            "India IT software services exports 2025",
            "Indian IT companies AI generative revenue",
            "TCS Infosys Wipro HCL Tech results 2025",
        ],
        "company_query": "top IT software companies India NSE BSE",
        "policy_query": "India IT policy SEZ export incentives 2025",
    },
    "energy": {
        "news_queries": [
            "India renewable energy solar wind 2025",
            "Indian energy sector stocks power generation",
            "India green hydrogen energy transition 2025",
        ],
        "company_query": "top energy power renewable companies India NSE",
        "policy_query": "India energy policy renewable target government 2025",
    },
    "retail": {
        "news_queries": [
            "India retail sector consumer spending 2025",
            "Indian retail companies ecommerce growth",
            "India organized retail market outlook 2025",
        ],
        "company_query": "top retail companies India NSE BSE listed",
        "policy_query": "India retail FDI policy ecommerce regulation 2025",
    },
    "infrastructure": {
        "news_queries": [
            "India infrastructure capex spending 2025",
            "Indian infrastructure companies roads ports",
            "India National Infrastructure Pipeline projects",
        ],
        "company_query": "top infrastructure construction companies India NSE",
        "policy_query": "India infrastructure government budget capex 2025",
    },
    "fmcg": {
        "news_queries": [
            "India FMCG sector volume growth 2025",
            "Indian FMCG companies rural urban demand",
            "HUL Nestle ITC FMCG results India",
        ],
        "company_query": "top FMCG consumer goods companies India NSE BSE",
        "policy_query": "India FMCG GST consumer policy 2025",
    },
    "telecom": {
        "news_queries": [
            "India telecom sector 5G Jio Airtel 2025",
            "Indian telecom ARPU subscriber growth",
            "India 5G rollout spectrum telecom 2025",
        ],
        "company_query": "top telecom companies India NSE BSE listed",
        "policy_query": "India telecom policy spectrum allocation 2025",
    },
    "metals": {
        "news_queries": [
            "India metals mining steel sector 2025",
            "Indian metals companies Tata Steel JSW earnings",
            "India steel aluminium demand export 2025",
        ],
        "company_query": "top metals mining steel companies India NSE BSE",
        "policy_query": "India metals import duty mining policy 2025",
    },
}

# Generic fallback for unlisted sectors
_GENERIC_TEMPLATE = {
    "news_queries": [
        "India {sector} sector stocks market 2025",
        "Indian {sector} companies growth outlook",
        "{sector} industry India trade opportunities 2025",
    ],
    "company_query": "top {sector} companies India NSE BSE listed",
    "policy_query": "India {sector} government policy regulation 2025",
}


class MarketDataCollector:
    def __init__(self):
        self._cache: Dict[str, dict] = {}

    def _get_template(self, sector: str) -> dict:
        if sector in SECTOR_SEARCH_TEMPLATES:
            return SECTOR_SEARCH_TEMPLATES[sector]
        # Build generic template
        t = _GENERIC_TEMPLATE
        return {
            "news_queries": [q.format(sector=sector) for q in t["news_queries"]],
            "company_query": t["company_query"].format(sector=sector),
            "policy_query": t["policy_query"].format(sector=sector),
        }

    def _search_sync(self, query: str, max_results: int = 5) -> List[dict]:
        """Run a DuckDuckGo text search synchronously."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            logger.info(f"Search '{query[:50]}...' → {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search failed for '{query}': {e}")
            return []

    def _extract_companies(self, results: List[dict]) -> List[str]:
        """Parse company names from search result snippets."""
        companies = []
        seen = set()
        # Common Indian listed company indicators
        indicators = ["Ltd", "Limited", "Corp", "Industries", "Technologies", "Services", "Bank", "Finance"]
        for r in results:
            text = (r.get("title", "") + " " + r.get("body", ""))
            words = text.split()
            for i, word in enumerate(words):
                if any(ind in word for ind in indicators) and i > 0:
                    name = f"{words[i-1]} {word}"
                    if name not in seen and len(name) > 5:
                        companies.append(name)
                        seen.add(name)
                if len(companies) >= 8:
                    break
            if len(companies) >= 8:
                break
        return companies[:8]

    def _extract_trends(self, results: List[dict]) -> List[str]:
        """Extract trend phrases from headlines."""
        trends = []
        seen = set()
        keywords = ["growth", "surge", "decline", "expansion", "adoption", "demand",
                    "investment", "innovation", "recovery", "momentum", "outlook"]
        for r in results:
            title = r.get("title", "")
            for kw in keywords:
                if kw.lower() in title.lower():
                    short = title[:80].strip()
                    if short not in seen:
                        trends.append(short)
                        seen.add(short)
                    break
            if len(trends) >= 6:
                break
        return trends[:6]

    def _extract_policies(self, results: List[dict]) -> List[str]:
        """Extract policy/government initiative mentions."""
        policies = []
        seen = set()
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")[:200]
            combined = f"{title}: {body}"[:150].strip()
            if combined not in seen:
                policies.append(combined)
                seen.add(combined)
            if len(policies) >= 4:
                break
        return policies[:4]

    def _detect_sentiment(self, results: List[dict]) -> str:
        positive_words = {"growth", "surge", "rally", "bullish", "record", "gains",
                          "strong", "beat", "positive", "rise", "increase", "profit"}
        negative_words = {"decline", "fall", "drop", "bearish", "loss", "weak",
                          "miss", "negative", "concern", "risk", "cut", "slump"}
        pos = neg = 0
        for r in results:
            text = (r.get("title", "") + " " + r.get("body", "")).lower()
            pos += sum(1 for w in positive_words if w in text)
            neg += sum(1 for w in negative_words if w in text)
        if pos > neg * 1.5:
            return "positive"
        elif neg > pos * 1.5:
            return "negative"
        return "neutral"

    async def search_market_data(self, sector: str) -> MarketData:
        """
        Perform real-time DuckDuckGo searches to collect live market data
        for the requested sector. Results are cached for CACHE_TTL_SECONDS.
        """
        # Cache check
        cached = self._cache.get(sector)
        if cached and (time.time() - cached["ts"]) < Config.CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for sector '{sector}'")
            return cached["data"]

        logger.info(f"Fetching live market data for sector: {sector}")
        template = self._get_template(sector)

        # Run all searches concurrently using asyncio threads
        loop = asyncio.get_event_loop()

        news_tasks = [
            loop.run_in_executor(None, self._search_sync, q, Config.SEARCH_MAX_RESULTS)
            for q in template["news_queries"]
        ]
        company_task = loop.run_in_executor(None, self._search_sync, template["company_query"], 8)
        policy_task = loop.run_in_executor(None, self._search_sync, template["policy_query"], 5)

        all_news_results, company_results, policy_results = await asyncio.gather(
            asyncio.gather(*news_tasks),
            company_task,
            policy_task
        )

        # Flatten news results from all queries, deduplicate by title
        seen_titles: set = set()
        flat_news: List[NewsItem] = []
        for results in all_news_results:
            for r in results:
                title = r.get("title", "").strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    flat_news.append(NewsItem(
                        title=title,
                        summary=r.get("body", "")[:300],
                        source=r.get("source", r.get("href", "unknown")),
                        url=r.get("href")
                    ))

        all_results_flat = [r for batch in all_news_results for r in batch]

        companies = self._extract_companies(company_results)
        trends = self._extract_trends(all_results_flat)
        policies = self._extract_policies(policy_results)
        sentiment = self._detect_sentiment(all_results_flat)

        market_data = MarketData(
            sector=sector,
            news_summary=flat_news[:15],
            key_companies=companies,
            trends=trends,
            government_policies=policies,
            market_sentiment=sentiment
        )

        # Cache result
        self._cache[sector] = {"data": market_data, "ts": time.time()}
        logger.info(
            f"Data collection complete for '{sector}': "
            f"{len(flat_news)} news items, {len(companies)} companies"
        )
        return market_data
