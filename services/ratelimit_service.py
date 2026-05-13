from pydantic import BaseModel
from redis.asyncio import Redis
from config import settings
from typing import cast
from database.auth import UserApiKey
from responses import RateLimitedError
import logging

logger = logging.getLogger(__name__)

class RateLimit(BaseModel):
    remaining: int
    expiration: float
    
    @property
    def ratelimited(self) -> bool:
        return self.remaining == 0

async def _check_rate_limit(redis: Redis, key: str, rate: int | None = None, per: int | None = None):
    current = cast(int, await redis.incrby(key))
    
    if current == 1:
        logger.debug("Initializing rate limit for key.", extra={"identifier": key.split(':', 1)[1]})
        await redis.expire(key, per or settings.per_seconds)
    expiration = cast(float, await redis.pttl(key)) / 1000
    
    if current > (rate or settings.rate_limit):
        logger.warning(
            "Rate limit exceeded for key.", 
            extra={"identifier": key.split(':', 1)[1], "current": current, "expiration": expiration}
        )
        raise RateLimitedError(message="Rate limit exceeded", retry_after=expiration)
    
    return RateLimit(remaining=settings.rate_limit - current, expiration=expiration)

async def check_key_rate_limit(redis: Redis, user_key: UserApiKey, rate: int | None = None, per: int | None = None):
    """Raises `RateLimitedError` (`HTTPException`) if `key_id` is exceeding rate limits - 
    setting `rate` or `per` overrides settings. Returns number of requests left and request expiration as a tuple."""
    key = f"key_rate_limit:{user_key.key_id}"
    logger.debug("Checking rate limit for key.", extra={"key_id": user_key.key_id})
    return await _check_rate_limit(redis, key, rate, per)
    
async def check_ip_rate_limit(redis: Redis, ip: str, rate: int | None = None, per: int | None = None):
    """Raises `RateLimitedError` (`HTTPException`) if `ip` is exceeding rate limits - 
    setting `rate` or `per` overrides settings. Returns number of requests left and request expiration as a tuple."""
    key = f"ip_rate_limit:{ip}"
    logger.debug("Checking rate limit for IP.", extra={"ip": ip})
    return await _check_rate_limit(redis, key, rate, per)