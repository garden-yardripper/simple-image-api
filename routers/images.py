from typing import Annotated
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header, Query, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from database import images
from database.auth import UserApiKey, check_for_key
import database
from dependencies import get_db, get_redis
from responses import RateLimitInfoResponse
from services import image_service as service
from services.ratelimit_service import check_key_rate_limit, RateLimit
import os

router = APIRouter()

@router.post("/images")
async def create_image(
    request: Request,
    file: UploadFile,
    title: Annotated[str, Query(default=None, min_length=1, max_length=255)], 
    description: Annotated[str, Query(default=None, min_length=0, max_length=1000)], 
    private: Annotated[bool, Query(default=False)],
    api_key: Annotated[str, Header(default=None, alias="api-key")],
    db: Annotated[database.Database, Depends(get_db)],
    redis: Annotated[redis.Redis, Depends(get_redis)],
    user_key: Annotated[UserApiKey, Depends(check_for_key)],
    ratelimit: Annotated[RateLimit, Depends(check_key_rate_limit)]
):
    image = await service.validate_and_save_image(
        db, file, user_key, str(request.base_url), 
        title, description, private
    )
    
    return RateLimitInfoResponse(
        image.model_dump(), ratelimit.remaining, ratelimit.expiration
    )
    
@router.get("/images/{filename}")
async def get_image_id(
    filename: str, 
    db: Annotated[database.Database, Depends(get_db)],
    redis: Annotated[redis.Redis, Depends(get_redis)],
    api_key: Annotated[str, Header(default=None, alias="api-key")],
    user_key: Annotated[UserApiKey, Depends(check_for_key)],
    ratelimit: Annotated[RateLimit, Depends(check_key_rate_limit)]
):
    image_id, extension = os.path.splitext(filename)
    
    image = await images.get_image_data_from_id(db, image_id)
    if image is None:
        raise HTTPException(404, {"message": "Image not found"})
    
    if extension:
        return FileResponse(image.file_path, media_type=image.mime_type, filename=image.file_name)
    
    return JSONResponse(image.model_dump())