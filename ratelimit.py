from redis.asyncio import Redis
from config import settings
from typing import cast
from responses import RateLimitedError

async def _check_rate_limit(client: Redis, key: str, rate: int | None = None, per: int | None = None):
    current = cast(int, await client.incrby(key))
    
    if current == 1:
        await client.expire(key, per or settings.per_seconds)
    expiration = cast(float, await client.pttl(key)) / 1000
    
    if current > (rate or settings.rate_limit):
        raise RateLimitedError(message="Rate limit exceeded", retry_after=expiration)
    return settings.rate_limit - current, expiration

async def check_key_rate_limit(client: Redis, key_id: str, rate: int | None = None, per: int | None = None):
    """Raises `RateLimitedError` (`HTTPException`) if `key_id` is exceeding rate limits - 
    setting `rate` or `per` overrides settings. Returns number of requests left and request expiration as a tuple."""
    key = f"key_rate_limit:{key_id}"
    return await _check_rate_limit(client, key, rate, per)
    
async def check_ip_rate_limit(client: Redis, ip: str, rate: int | None = None, per: int | None = None):
    """Raises `RateLimitedError` (`HTTPException`) if `ip` is exceeding rate limits - 
    setting `rate` or `per` overrides settings. Returns number of requests left and request expiration as a tuple."""
    key = f"ip_rate_limit:{ip}"
    return await _check_rate_limit(client, key, rate, per)