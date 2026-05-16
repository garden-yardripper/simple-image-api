from pydantic import BaseModel, field_validator, field_serializer
from .database import Database
from urllib.parse import urljoin
from datetime import datetime
from typing import Any
import logging

logger = logging.getLogger(__name__)

class Image(BaseModel):
    image_id: str
    key_id: str
    file_path: str
    file_name: str | None
    file_size: int | None
    mime_type: str | None
    title: str | None
    description: str | None
    private: bool
    uploaded: datetime
    updated: datetime
    
    @classmethod
    @field_validator("uploaded", "updated", mode="before")
    def convert_timestamp_to_datetime(cls, value):
        if isinstance(value, float) or isinstance(value, int):
            return datetime.fromtimestamp(value)
        return value
    
    @field_serializer("uploaded", "updated")
    def serialize_datetime_to_timestamp(self, time: datetime) -> float:
        return time.timestamp()
    
    def model_dump(self, *, include=None, exclude=None, **kwargs) -> dict[str, Any]:
        if exclude is None:
            exclude = {"key_id", "file_path", "file_size"}
        return super().model_dump(include=include, exclude=exclude, **kwargs)
    
    @classmethod
    async def from_id(cls, db: Database, image_id: str) -> "Image":
        """Return an `Image` object with the specified image_id. Raises `ValueError` if no image is found."""
        result = await db.fetchone("SELECT * FROM images WHERE image_id = %s", (image_id,))
        if not result:
            logger.debug("No image found in database with specified image ID.", extra={"image_id": image_id})
            raise ValueError(f"No image found in database with specified image ID: {image_id}")
        
        logger.debug("Returning found image metadata.", extra=result)
        return Image.model_validate(result)

class UploadedImage(BaseModel):
    image_id: str
    hosted_link: str
    mimetype: str | None
    title: str | None
    description: str | None
    private: bool

async def store_image_metadata(
    db: Database,
    image_id: str,
    key_id: str,
    base_url: str,
    file_extension: str,
    file_path: str,
    file_name: str | None,
    file_size: int | None,
    mime_type: str | None,
    title: str | None,
    description: str | None,
    private: bool
) -> UploadedImage:
    """Returns the UploadedImage object."""
    
    await db.execute("""
        INSERT INTO images (
            image_id, key_id, file_path, file_name, 
            file_size, mime_type, title, description, private
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
        (image_id, key_id, file_path, file_name, file_size, mime_type, title, description, private)
    )
    
    image = UploadedImage(
        image_id=image_id,
        hosted_link=urljoin(base_url, f"images/{image_id}.{file_extension}"),
        mimetype=mime_type,
        title=title,
        description=description,
        private=private
    )
    logger.debug("Image metadata stored to database.", image.model_dump())
            
    return image