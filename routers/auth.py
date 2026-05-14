from fastapi import APIRouter, Depends, Query
from database import auth
from database.database import Database
from services.ratelimit_service import RateLimit, check_ip_rate_limit
from responses import RateLimitInfoResponse
from dependencies import get_db
from typing import Annotated

router = APIRouter()

@router.get("/api-key")
async def create_api_key(
    username: Annotated[str, Query()],
    db: Annotated[Database, Depends(get_db)],
    limit: Annotated[RateLimit, Depends(check_ip_rate_limit)]
):
    key = await auth.create_and_store_key(db, username, auth.KeyType.dev)
    return RateLimitInfoResponse({"api-key": key.full_key}, limit.remaining, limit.expiration)