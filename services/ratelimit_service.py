from pydantic import BaseModel
from redis.asyncio import Redis
from config import settings
from typing import cast
from database.auth import UserApiKey
from database.database import Database
from responses import RateLimitedError
from auth_service import check_for_key

class RateLimit(BaseModel):
    remaining: int
    expiration: float
    
    @property
    def ratelimited(self) -> bool:
        return self.remaining == 0

async def _check_rate_limit(client: Redis, key: str, rate: int | None = None, per: int | None = None):
    current = cast(int, await client.incrby(key))
    
    if current == 1:
        await client.expire(key, per or settings.per_seconds)
    expiration = cast(float, await client.pttl(key)) / 1000
    
    if current > (rate or settings.rate_limit):
        raise RateLimitedError(message="Rate limit exceeded", retry_after=expiration)
    return RateLimit(remaining=settings.rate_limit - current, expiration=expiration)

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

async def check_key_and_rate_limit(
    db: Database, client: Redis, key: str, 
    rate: int | None = None, per: int | None = None
) -> tuple[UserApiKey, RateLimit]:
    """Calls `check_for_key` and then checks the key's ratelimit with `check_key_rate_limit`. 
    Returns a tuple containing the `UserApiKey` and `RateLimit` objects."""
    user_key = await check_for_key(db, key)
    ratelimit = await check_key_rate_limit(client, user_key.key_id, rate, per)
    return user_key, ratelimit