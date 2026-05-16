from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse
from database.images import Image
from database.auth import UserApiKey, check_for_key
from database.database import Database
from dependencies import get_db
from responses import RateLimitInfoResponse
from services import image_service as service
from services.ratelimit_service import check_key_rate_limit, RateLimit
from services.search_service import search
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

@router.get("/images/explore")
async def explore_images(
    db: Annotated[Database, Depends(get_db)],
    use_and: Annotated[bool, Query()] = False,
    image_id: Annotated[str | None, Query()] = None,
    title: Annotated[str | None, Query()] = None,
    description: Annotated[str | None, Query()] = None,
    username: Annotated[str | None, Query()] = None,
    file_name: Annotated[str | None, Query()] = None,
    mime_type: Annotated[str | None, Query()] = None,
    uploaded_before: Annotated[datetime | None, Query()] = None,
    uploaded_after: Annotated[datetime | None, Query()] = None,
    updated_before: Annotated[datetime | None, Query()] = None,
    updated_after: Annotated[datetime | None, Query()] = None,
    file_size_greater: Annotated[int | None, Query()] = None,
    file_size_less: Annotated[int | None, Query()] = None
):
    results = await search(
        db, use_and,
        image_id=image_id,
        title=title,
        description=description,
        username=username,
        file_name=file_name,
        mime_type=mime_type,
        uploaded_before=uploaded_before,
        uploaded_after=uploaded_after,
        updated_before=updated_before,
        updated_after=updated_after,
        file_size_greater=file_size_greater,
        file_size_less=file_size_less
    )
    image_list: list[Image] = []
    
    for result in results:
        image = Image.model_validate(result)
        image_list.append(image)

    logger.debug("Returning search results.", extra={"result_count": len(image_list)})
    return image_list

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
    
    image = await Image.from_id(db, image_id)
    if image is None:
        logger.debug("No image found with specified ID.", extra={"image_id": image_id})
        raise HTTPException(404, {"message": "Image not found"})
    
    if extension:
        logger.debug("Returning image file.", extra={"image_id": image_id, "file_path": image.file_path})
        return FileResponse(image.file_path, media_type=image.mime_type, filename=image.file_name)
    
    image_data = image.model_dump()
    logger.debug("Returning image metadata.", extra=image_data)
    return RateLimitInfoResponse(image_data, ratelimit.remaining, ratelimit.expiration)