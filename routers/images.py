from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from database.images import Image
from database.auth import UserApiKey, check_for_key
from database.database import Database
from dependencies import get_db
from responses import RateLimitInfoResponse
from services import image_service as service
from services.ratelimit_service import check_key_rate_limit, RateLimit
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/images")
async def create_image(
    request: Request,
    file: UploadFile,
    title: Annotated[str, Query(min_length=1, max_length=255)], 
    description: Annotated[str, Query(min_length=0, max_length=1000)], 
    db: Annotated[Database, Depends(get_db)],
    user_key: Annotated[UserApiKey, Depends(check_for_key)],
    ratelimit: Annotated[RateLimit, Depends(check_key_rate_limit)],
    private: Annotated[bool, Query()] = False
):
    logger.debug(
        "Received request to upload image.", 
        extra={"key_id": user_key.key_id, "image_filename": file.filename}
    )
    image = await service.validate_and_save_image(
        db, file, user_key, str(request.base_url), 
        title, description, private
    )
    
    image_data = image.model_dump()
    logger.debug("Returning uploaded image metadata.", extra=image_data)
    return RateLimitInfoResponse(
        image_data, ratelimit.remaining, ratelimit.expiration
    )
    
@router.get("/images/{filename}")
async def get_image_id(
    filename: str, 
    db: Annotated[Database, Depends(get_db)],
    user_key: Annotated[UserApiKey, Depends(check_for_key)],
    ratelimit: Annotated[RateLimit, Depends(check_key_rate_limit)],
):
    logger.debug(
        "Received request to retrieve image.", 
        extra={"key_id": user_key.key_id, "image_filename": filename}
    )
    image_id, extension = os.path.splitext(filename)
    
    image = await Image.get_image_data_from_id(db, image_id)
    if image is None:
        logger.debug("No image found with specified ID.", extra={"image_id": image_id})
        raise HTTPException(404, {"message": "Image not found"})
    
    if extension:
        logger.debug("Returning image file.", extra={"image_id": image_id, "file_path": image.file_path})
        return FileResponse(image.file_path, media_type=image.mime_type, filename=image.file_name)
    
    image_data = image.model_dump()
    logger.debug("Returning image metadata.", extra=image_data)
    return JSONResponse(image_data)