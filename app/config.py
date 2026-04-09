import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-insecure-default")
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    SUPPORTED_SECTORS: set = {
        "pharmaceuticals", "technology", "agriculture",
        "banking", "automobile", "it", "energy", "retail",
        "infrastructure", "fmcg", "telecom", "metals"
    }

    @classmethod
    def validate(cls):
        warnings = []
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY not set — AI analysis will use fallback mode")
        if cls.SECRET_KEY == "changeme-insecure-default":
            warnings.append("SECRET_KEY is using insecure default — set it in .env for production")
        for msg in warnings:
            logger.warning(msg)
        return warnings
