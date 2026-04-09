from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import logging
import os

from .auth import get_or_create_session

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_SECTORS = [
    "pharmaceuticals", "technology", "agriculture", "banking",
    "automobile", "it", "energy", "retail", "infrastructure",
    "fmcg", "telecom", "metals"
]


@router.get("/analyze/{sector}", response_model=dict)
async def analyze_sector(
    sector: str,
    request: Request,
    session: dict = Depends(get_or_create_session)
):
    """
    Analyze a sector and return markdown report with trade opportunities
    
    **Parameters:**
    - sector: Name of the sector (e.g., 'pharmaceuticals', 'technology')
    
    **Returns:**
    - Structured markdown report with market analysis and trade opportunities
    """
    
    # Validate sector
    sector_lower = sector.lower().strip()
    if sector_lower not in VALID_SECTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sector. Valid options: {', '.join(VALID_SECTORS)}"
        )
    
    # Check rate limit
    rate_limiter = request.app.state.rate_limiter
    if not rate_limiter.is_allowed(session["session_id"]):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 10 requests per 60 seconds"
        )
    
    # Get or create analysis cache
    if not hasattr(request.app.state, 'analysis_cache'):
        request.app.state.analysis_cache = {}
    
    analysis_cache = request.app.state.analysis_cache
    
    # Check cache
    cache_key = f"{sector_lower}_{datetime.now().strftime('%Y-%m-%d-%H')}"
    
    if cache_key in analysis_cache:
        logger.info(f"✓ Cache hit for sector: {sector_lower}")
        return analysis_cache[cache_key]
    
    try:
        # Import here to avoid circular imports
        from main import SearchClient, MarketAnalyzer
        
        # Search for market data using multiple APIs
        search_query = f"{sector_lower} sector market news India trade opportunities 2026"
        logger.info(f"🔍 Searching for: {search_query}")
        
        search_client = request.app.state.search_client
        search_results = await search_client.search(search_query)
        
        if not search_results:
            raise HTTPException(status_code=503, detail="No market data available")
        
        logger.info(f"📊 Found {len(search_results)} market sources")
        
        # Analyze with AI or fallback
        analyzer = MarketAnalyzer()
        report = await analyzer.analyze_sector(sector_lower, search_results)
        
        # Create response
        response = {
            "sector": sector_lower,
            "report": report,
            "data_sources": len(search_results),
            "timestamp": datetime.now().isoformat(),
            "session_id": session["session_id"],
            "ai_powered": analyzer.use_gemini
        }
        
        # Cache the result
        analysis_cache[cache_key] = response
        request.app.state.analysis_cache = analysis_cache
        
        logger.info(f"✅ Analysis completed for sector: {sector_lower}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/sectors")
async def get_sectors(request: Request, session: dict = Depends(get_or_create_session)):
    """Get list of supported sectors"""
    return {
        "sectors": VALID_SECTORS,
        "count": len(VALID_SECTORS),
        "session_id": session["session_id"]
    }