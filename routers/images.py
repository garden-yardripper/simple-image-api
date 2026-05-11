from typing import Annotated
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, Query, Request, UploadFile
import database
import ratelimit
from dependencies import get_db, get_redis
from responses import RateLimitInfoResponse
from services import image_service as service
from services.auth_service import check_for_key

router = APIRouter()

@router.post("/images")
async def create_image(
    request: Request,
    file: UploadFile,
    title: Annotated[str, Query(default=None, min_length=1, max_length=255)], 
    description: Annotated[str, Query(default=None, min_length=0, max_length=1000)], 
    private: Annotated[bool, Query(default=False)],
    api_key: Annotated[str, Header(default=None, alias="api-key")],
    db: database.Database = Depends(get_db),
    redis: redis.Redis = Depends(get_redis)
):
    user_key = await check_for_key(db, api_key)
    remaining, expiration = await ratelimit.check_key_rate_limit(redis, user_key.key_id)
    
    image = await service.validate_and_save_image(
        db, file, user_key, str(request.base_url), 
        title, description, private
    )
    
    return RateLimitInfoResponse(
        image.model_dump(), remaining, expiration
    )