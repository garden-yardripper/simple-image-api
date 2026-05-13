from fastapi import UploadFile, HTTPException
from PIL import Image as PILImage
from io import BytesIO
import mimetypes
import asyncio
import uuid
import os
import aiofiles
from config import settings
from database import images
from database.auth import UserApiKey
from database.database import Database
import logging

logger = logging.getLogger(__name__)

async def is_valid_image(file: bytes) -> bool:
    def _run():
        try:
            with PILImage.open(BytesIO(file)) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)

async def validate_and_save_image(
    db: Database, file: UploadFile, user_key: UserApiKey, base_url: str,
    title: str, description: str, private: bool
) -> images.UploadedImage:
    if not file.filename:
        logger.info("Uploaded file missing filename.", extra={"key_id": user_key.key_id})
        raise HTTPException(400, {"message": "Uploaded image must have a filename."})
    
    filename, extension = os.path.splitext(file.filename)
    if not extension:
        logger.info("Uploaded file missing extension.", extra={"key_id": user_key.key_id})
        raise HTTPException(400, {"message": "Uploaded file must have a valid extension."})
    
    extension = extension.lstrip(".").lower()
    mimetype, _ = mimetypes.guess_type(file.filename)
    
    acceptable_extensions = {"png", "jpg", "jpeg", "gif", "webp", "avif"}
    if extension not in acceptable_extensions:
        logger.info(
            "Uploaded file has unsupported extension.", 
            extra={"key_id": user_key.key_id, "extension": extension}
        )
        raise HTTPException(415, {"message": "Image type unsupported."})

    # validate file size is less than 10MiB
    max_size = 10 * 1024 ** 2 # 10MiB
    bytes_read = 0
    while True:
        if bytes_read > max_size:
            logger.info("Image file size exceeds 10MB limit.", extra={"key_id": user_key.key_id})
            raise HTTPException(413, {"message": "Image file size exceeds 10MB limit."})
        
        contents = await file.read(1024 ** 2)
        contents_len = len(contents)
        bytes_read += contents_len
        
        if contents_len < 1024 ** 2:
            break # EOF reached
    
    await file.seek(0)
    file_bytes = await file.read()
    if not await is_valid_image(file_bytes):
        logger.info("Uploaded file is not a valid image or is malformed.", extra={"key_id": user_key.key_id})
        raise HTTPException(400, {"message": "Uploaded file is not a valid image or is malformed."})
    
    image_id = str(uuid.uuid4())
    path = os.path.join(settings.image_directory, f"{image_id}.{extension}")
    
    logger.info("Saving image file.", extra={"key_id": user_key.key_id, "image_id": image_id})
    async with aiofiles.open(path, "wb") as f:
        await f.write(file_bytes)
        
    image = await images.store_image_metadata(
        db, image_id, user_key.key_id, str(base_url), extension,
        path, filename, bytes_read, mimetype, title, description, private
    )
    logger.info("Image metadata stored.", extra={"key_id": user_key.key_id, "image_id": image_id})
    return image